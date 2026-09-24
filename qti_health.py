"""Check the platform dependency before constructing the native QTI source.

This prevents the known missing-recorder startup path. It is not process
isolation and cannot contain arbitrary crashes inside vendor native libraries.
"""
import subprocess


def require_recorder_service():
    try:
        result = subprocess.run(
            ['systemctl', 'is-active', 'qmmf_recorder.service'],
            capture_output=True, text=True, timeout=3, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(
            '無法確認 qmmf_recorder.service 狀態，已停止相機啟動；'
            '請在設備上確認 recorder service 後重試'
        ) from exc
    if result.returncode != 0 or result.stdout.strip() != 'active':
        state = result.stdout.strip() or 'unknown'
        raise RuntimeError(
            f'qmmf_recorder.service 尚未就緒（{state}），已停止相機啟動；'
            '請檢查 systemctl status qmmf_recorder.service 與服務日誌'
        )
