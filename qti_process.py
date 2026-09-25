"""QTI native code runs in a disposable spawned process, never the HTTP process.

Frames use bounded shared memory without recompression. Native crashes/timeouts
are reported to the runtime; there is deliberately no automatic restart loop.
"""
import importlib
import multiprocessing as mp
import threading
import time
from pathlib import Path
import numpy as np


def _worker(cfg, conn, pixels, shape, frame_lock, factory):
    backend = None
    try:
        module, name = factory
        backend = getattr(importlib.import_module(module), name)(cfg)
        backend.start()
        conn.send({'ok': True, 'value': backend.status()})
        seq = 0
        while True:
            if conn.poll():
                command, arg = conn.recv()
                try:
                    if command == 'stop':
                        backend.stop(); backend = None
                        conn.send({'ok': True, 'value': None}); break
                    if command == 'record_start': value = backend.start_recording(Path(arg))
                    elif command == 'record_stop': value = backend.stop_recording()
                    elif command == 'controls': value = backend.apply_controls(*arg)
                    elif command == 'status': value = backend.status()
                    else: raise ValueError('Unknown camera command')
                    conn.send({'ok': True, 'value': value})
                except Exception as exc:
                    conn.send({'ok': False, 'error': str(exc)})
            frame = backend.read(timeout=.1)
            if frame is not None:
                frame = np.ascontiguousarray(frame, dtype=np.uint8)
                if frame.ndim != 3 or frame.shape[2] != 3 or frame.size > len(pixels):
                    raise RuntimeError('QTI frame exceeds configured shared buffer')
                with frame_lock:
                    np.frombuffer(pixels, dtype=np.uint8, count=frame.size)[:] = frame.reshape(-1)
                    seq += 1
                    shape[:] = [frame.shape[0], frame.shape[1], seq]
    except (EOFError, BrokenPipeError):
        pass
    except Exception as exc:
        try: conn.send({'ok': False, 'error': str(exc)})
        except (EOFError, BrokenPipeError): pass
    finally:
        if backend is not None: backend.stop()
        conn.close()


class QtiProcessBackend:
    name = 'qti'
    hardware_recording = True

    def __init__(self, cfg, factory=('edge_runtime', 'QtiGstCameraBackend')):
        self.cfg = cfg
        self.factory = factory
        self.process = None
        self.conn = None
        self._rpc_lock = threading.RLock()
        self._status = {'backend': 'qti', 'hardware_recording': True}
        self._seq = 0

    def _failure(self):
        code = self.process.exitcode if self.process else None
        return RuntimeError(f'QTI 相機程序已退出（exit={code}）；網頁服務仍在運作。請檢查設備端 QMMF 訊息後手動重試。')

    def _receive(self, timeout):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.conn.poll(.05):
                try: reply = self.conn.recv()
                except (EOFError, OSError): raise self._failure()
                if not reply['ok']: raise RuntimeError(reply['error'])
                return reply['value']
            if not self.process.is_alive(): raise self._failure()
        raise TimeoutError('QTI 相機程序回應逾時')

    def _rpc(self, command, arg=None, timeout=3):
        with self._rpc_lock:
            if not self.process or not self.process.is_alive(): raise self._failure()
            try:
                self.conn.send((command, arg))
                return self._receive(timeout)
            except (TimeoutError, EOFError, BrokenPipeError, OSError):
                # Do not allow a late reply to be mistaken for a later command.
                self._terminate()
                raise

    def start(self):
        ctx = mp.get_context('spawn')
        self.pixels = ctx.RawArray('B', max(1, self.cfg.width*self.cfg.height*3))
        self.shape = ctx.RawArray('q', 3)
        self.frame_lock = ctx.Lock()
        self.conn, child = ctx.Pipe()
        self.process = ctx.Process(target=_worker, args=(self.cfg, child, self.pixels, self.shape,
            self.frame_lock, self.factory), daemon=True, name='visionedge-qti')
        self.process.start(); child.close()
        try: self._status = self._receive(15)
        except Exception:
            self.stop(); raise

    def read(self, timeout=1):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not self.process or not self.process.is_alive(): raise self._failure()
            if not self.frame_lock.acquire(timeout=.1):
                if not self.process.is_alive(): raise self._failure()
                continue
            try:
                h, w, seq = self.shape[:]
                if h and w and seq != self._seq:
                    self._seq = seq
                    return np.frombuffer(self.pixels, dtype=np.uint8, count=h*w*3).reshape(h,w,3).copy()
            finally: self.frame_lock.release()
            time.sleep(.005)
        return None

    def status(self):
        # Runtime status holds its own lock. Never block it on child IPC.
        result = dict(self._status)
        if self.process and not self.process.is_alive():
            result.update(recording=False, last_error=str(self._failure()))
        return result

    def apply_controls(self, mode, values):
        result = self._rpc('controls', (mode, values))
        if result.get('applied'): self._status['camera_controls'] = result['report']
        return result

    def start_recording(self, path):
        ok, message = self._rpc('record_start', str(path), timeout=6)
        if ok: self._status.update(recording=True, record_path=str(path))
        return ok, message

    def stop_recording(self):
        result = self._rpc('record_stop', timeout=7)
        self._status.update(recording=False, record_path='')
        return result

    def _terminate(self):
        if self.process and self.process.is_alive():
            self.process.terminate(); self.process.join(1)
            if self.process.is_alive(): self.process.kill(); self.process.join(1)

    def stop(self):
        with self._rpc_lock:
            try:
                if self.process and self.process.is_alive(): self._rpc('stop', timeout=3)
            except Exception: pass
            finally:
                if self.process: self.process.join(.5)
                self._terminate()
                if self.conn: self.conn.close()
                self._status.update(recording=False)
