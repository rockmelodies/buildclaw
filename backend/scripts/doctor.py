from __future__ import annotations
"""BuildClaw environment doctor.

This script validates whether the current machine is ready to run deployment
workloads before the service is started or reloaded.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import load_config  # noqa: E402
from app.runtime_checks import collect_runtime_checks, prepare_runtime_directories  # noqa: E402


def main() -> int:
    try:
        config = load_config()
        prepare_runtime_directories(config)
        report = collect_runtime_checks(config)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2, ensure_ascii=False))
        return 1

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
