"""Image-gated packaging cycles. No absence-by-mismatch, no timed auto-rearm."""
import copy
import json
import math
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path


DEFAULTS = dict(enabled=False, mode='box', vacant_region_id=0, ready_region_id=0,
                presence_region_id=0, stable_sec=0.8, final_sec=1.0, margin=8,
                final_step_numbers=[])


def ensure_schema(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS packaging_settings(product_id INTEGER PRIMARY KEY, config TEXT NOT NULL)')


def load_settings(conn, pid):
    exists = conn.execute("SELECT 1 FROM sqlite_master WHERE name='packaging_settings'").fetchone()
    row = conn.execute('SELECT config FROM packaging_settings WHERE product_id=?', (pid,)).fetchone() if exists else None
    return {**DEFAULTS, **(json.loads(row[0]) if row else {})}


def validate_settings(conn, pid, cfg, steps, sop_enabled):
    if not isinstance(cfg, dict):
        raise ValueError('包裝循環設定格式錯誤')
    c = {**DEFAULTS, **{k: v for k, v in cfg.items() if k in DEFAULTS}}
    if not isinstance(c['enabled'], bool):
        raise ValueError('包裝循環開關格式錯誤')
    if not c['enabled']:
        return c
    if not sop_enabled or not any(s.get('enabled', True) and s.get('required', True) for s in steps):
        raise ValueError('影像包裝循環需要啟用依序檢測，且至少有一個必要步驟')
    if c['mode'] not in ('box', 'fixture'):
        raise ValueError('包裝站類型無效')
    for field in ('stable_sec', 'final_sec'):
        value = float(c[field])
        if not math.isfinite(value) or not .3 <= value <= 10:
            raise ValueError('穩定時間必須介於 0.3 到 10 秒')
        c[field] = value
    margin = int(c['margin'])
    if not 1 <= margin <= 100:
        raise ValueError('位置容許偏移必須介於 1 到 100 像素')
    c['margin'] = margin
    roles = ['vacant_region_id', 'presence_region_id']
    if c['mode'] == 'box':
        roles.append('ready_region_id')
    for key in roles:
        c[key] = int(c[key])
        row = conn.execute('SELECT template_b64 FROM regions WHERE id=? AND product_id=?', (c[key], pid)).fetchone()
        if not row or not row[0]:
            raise ValueError('請先設定工作區清空、箱子就位與定位特徵所需的樣板')
    if len({c[k] for k in roles}) != len(roles):
        raise ValueError('不同觸發條件請使用不同樣板，避免條件衝突')
    if not isinstance(c['final_step_numbers'], list):
        raise ValueError('最終確認步驟格式錯誤')
    numbers = sorted(set(int(x) for x in c['final_step_numbers']))
    valid = {int(s.get('step_no') or i+1) for i, s in enumerate(steps) if s.get('enabled', True)}
    if not numbers or any(n not in valid for n in numbers):
        raise ValueError('至少選擇一個啟用步驟作為最後可見的確認條件')
    c['final_step_numbers'] = numbers
    return c


def save_settings(conn, pid, cfg):
    ensure_schema(conn)
    conn.execute('INSERT INTO packaging_settings VALUES (?,?) ON CONFLICT(product_id) DO UPDATE SET config=excluded.config',
                 (pid, json.dumps(cfg, ensure_ascii=False)))


class CycleJournal:
    """Each event, its evidence, and cycle status commit together."""
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS cycles(
                id TEXT PRIMARY KEY, product_id INTEGER, created REAL, updated REAL,
                status TEXT, metadata TEXT);
                CREATE TABLE IF NOT EXISTS events(
                id TEXT PRIMARY KEY, cycle_id TEXT, created REAL, kind TEXT,
                metadata TEXT, raw BLOB, result BLOB);
                CREATE INDEX IF NOT EXISTS event_cycle ON events(cycle_id,created);''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA synchronous=FULL')
        try:
            with db:
                yield db
        finally:
            db.close()

    def recover(self, pid):
        with self.connect() as db:
            db.execute("UPDATE cycles SET status='INTERRUPTED',updated=? WHERE product_id=? AND status IN ('IN_PROGRESS','READY')", (time.time(), pid))

    def record(self, cycle_id, pid, status, event, metadata, raw=b'', result=b''):
        now = time.time()
        payload = json.dumps(metadata, ensure_ascii=False, default=str)
        with self.connect() as db:
            db.execute('INSERT INTO cycles VALUES (?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET updated=excluded.updated,status=excluded.status,metadata=excluded.metadata',
                       (cycle_id, pid, now, now, status, payload))
            db.execute('INSERT INTO events VALUES (?,?,?,?,?,?,?)',
                       (uuid.uuid4().hex, cycle_id, now, event, payload, raw, result))


class PackagingCycle:
    def __init__(self, engine, cfg, record, now_fn=time.monotonic):
        self.engine = engine
        self.cfg = copy.deepcopy(cfg)
        # Packaging cannot complete by a timer, ignore ordering, or lose an alarm automatically.
        self.engine.config.update(auto_reset_mode='MANUAL', strict_order=True, alarm_on_skip=True, alarm_latch=True)
        for step in self.engine.steps_cfg:
            step['allow_out_of_order'] = False
        self.record = record
        self.now_fn = now_fn
        self.lock = threading.RLock()
        self.state = 'WAIT_CLEAR'
        self.cycle_id = None
        self.holds = {}
        self.last_ts = None
        self.active_clock = 0.0
        self.last_valid = False
        self.done_saved = set()
        self.last_result = ''
        self.pause_reason = ''
        self.evidence = {}
        self.error = ''
        self.final_generation = 0
        self.alarm_saved = None

    def stable(self, key, condition, now, seconds):
        if not condition:
            self.holds.pop(key, None)
            return False
        start, count = self.holds.get(key, (now, 0))
        self.holds[key] = (start, count+1)
        return count+1 >= 3 and now - start >= seconds

    def emit(self, event, status, evidence):
        self.record(self.cycle_id, status, event, {'settings': self.cfg, 'sop': self.engine.summary(),
                    'signals': self.evidence, 'cycle_state': self.state}, evidence)

    def interrupt(self, reason='影像中斷，請清空工作區後重新開始'):
        with self.lock:
            self.holds.clear()
            self.last_valid = False
            self.last_ts = None
            if self.cycle_id:
                try:
                    self.emit('INTERRUPTED', 'INTERRUPTED', None)
                except Exception as exc:
                    self.error = str(exc)
                    self.state = 'FAULT'
                    return
            self.cycle_id = None
            self.state = 'WAIT_CLEAR'
            self.pause_reason = reason
            self.engine.reset(reason='PACKAGING_INTERRUPTED')

    def cancel(self):
        self.interrupt('已中止此箱，請清空工作區後重新開始')

    def acknowledge(self):
        with self.lock:
            if self.state == 'FAULT':
                return
            self.engine.acknowledge_alarm()
            self.holds.clear()

    def update(self, signals, rules, evidence=None, now=None):
        with self.lock:
            now = self.now_fn() if now is None else now
            try:
                return self._update(signals, rules, evidence, now)
            except Exception as exc:
                self.state = 'FAULT'
                self.error = str(exc)
                self.pause_reason = '紀錄保存失敗，循環已停止；請處理儲存問題後重新啟動相機'
                return self.summary()

    def _update(self, signals, rules, evidence, now):
        if self.state == 'FAULT':
            return self.summary()
        if self.last_ts is not None and now - self.last_ts > 3:
            self.interrupt('影像間隔過長，請清空工作區後重新開始')
            if self.state == 'FAULT':
                return self.summary()
        delta = max(0, now - self.last_ts) if self.last_ts is not None else 0
        self.last_ts = now
        self.evidence = dict(signals)
        passed = {int(r['id']) for r in rules if r.get('id') is not None and r.get('pass') and not r.get('hard_reject')}
        ng = any(r.get('hard_reject') for r in rules)
        vacant = bool(signals.get('vacant')) and not passed and not ng
        if self.cfg['mode'] == 'box':
            vacant = vacant and not signals.get('presence') and not signals.get('ready')
        present = bool(signals.get('presence')) and not vacant
        ready = present and not signals.get('vacant') and bool(signals.get('ready')) and not passed and not ng
        # Contradictory or unknown signals never advance the cycle or clear it.
        if signals.get('vacant') and (passed or ng or (self.cfg['mode'] == 'box' and signals.get('presence'))):
            present = ready = vacant = False
        clear = self.stable('clear', vacant, now, self.cfg['stable_sec'])
        self.pause_reason = ''
        if self.state == 'WAIT_CLEAR':
            if clear:
                self.state = 'WAIT_READY'
                self.holds.clear()
                self.engine.reset(reason='PACKAGING_CLEAR')
            return self.summary()
        if self.state == 'WAIT_READY':
            trigger = ready if self.cfg['mode'] == 'box' else (present and (bool(passed) or ng))
            if self.stable('start', trigger, now, self.cfg['stable_sec']):
                self.cycle_id = uuid.uuid4().hex
                self.state = 'ACTIVE'
                self.active_clock = time.time()
                self.engine.reset(reason='PACKAGING_START', now_ts=self.active_clock)
                self.engine.started_ts = self.engine.expected_since_ts = self.active_clock
                self.last_valid = False
                self.done_saved = set()
                self.alarm_saved = None
                self.holds.clear()
                self.emit('START', 'IN_PROGRESS', evidence)
            else:
                return self.summary()
        if clear:
            outcome = 'OK' if self.state == 'READY_TO_REMOVE' else 'INCOMPLETE'
            self.emit('REMOVED', outcome, evidence)
            self.last_result = outcome
            self.cycle_id = None
            self.state = 'WAIT_READY'
            self.holds.clear()
            self.last_valid = False
            self.engine.reset(reason='PACKAGING_REMOVED')
            return self.summary()
        if not present:
            if ng and self.state == 'READY_TO_REMOVE':
                self.state = 'ACTIVE'
                self.emit('FINAL_REVOKED', 'IN_PROGRESS', evidence)
            self.pause_reason = '畫面遮擋或定位特徵不明，等待清楚畫面'
            self.engine.interrupt(reason='PACKAGING_OCCLUDED')
            self.last_valid = False
            self.holds.pop('final', None)
            return self.summary()
        if self.last_valid:
            self.active_clock += delta
        self.last_valid = True
        summary = self.engine.update(rules, now_ts=self.active_clock)
        if summary['alarm']['active'] and summary['alarm']['seq'] != self.alarm_saved:
            self.emit('ALARM', 'IN_PROGRESS', evidence)
            self.alarm_saved = summary['alarm']['seq']
        for step in summary['steps']:
            if step['status'] == 'DONE' and step['id'] not in self.done_saved:
                self.emit('STEP_'+str(step['step_no']), 'IN_PROGRESS', evidence)
                self.done_saved.add(step['id'])
        final_ids = {s['id'] for s in self.engine.steps_cfg if s['step_no'] in self.cfg['final_step_numbers']}
        final_ok = summary['complete'] and bool(final_ids) and final_ids.issubset(passed) and not ng
        if self.state == 'READY_TO_REMOVE' and not final_ok:
            self.state = 'ACTIVE'
            self.holds.pop('final', None)
            self.emit('FINAL_REVOKED', 'IN_PROGRESS', evidence)
        if self.stable('final', final_ok, now, self.cfg['final_sec']) and self.state != 'READY_TO_REMOVE':
            self.state = 'READY_TO_REMOVE'
            self.emit('FINAL_VERIFIED', 'READY', evidence)
        elif summary['steps_complete'] and not final_ok and not summary['alarm']['active']:
            self.pause_reason = '步驟已完成，請確認最後應可見的物品仍在正確位置'
        return self.summary()

    def summary(self):
        with self.lock:
            sop = self.engine.summary()
            result = dict(enabled=True, mode=self.cfg['mode'], state=self.state,
                          cycle_id=self.cycle_id, last_result=self.last_result,
                          pause_reason=self.pause_reason, error=self.error, signals=dict(self.evidence))
            sop['complete'] = self.state == 'READY_TO_REMOVE' and not self.pause_reason
            sop['packaging'] = result
            return sop
