"""Run every project's tests, each in its own folder.

The projects cannot share one pytest run: both have a module called config,
and whichever loads first would be used by both. So each suite runs on its
own, from its own folder, and the results are summed here.

    python run_tests.py              offline
    python run_tests.py --network    also read the live store
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUITES = ["shared", "fantasy", "dss"]


def main() -> int:
    extra = sys.argv[1:]
    failed = []
    for suite in SUITES:
        print(f"\n=== {suite} ===", flush=True)
        args = [sys.executable, "-m", "pytest", "-q"]
        if suite == "shared":
            args += extra
        code = subprocess.call(args, cwd=ROOT / suite)
        if code not in (0, 5):          # 5 means no tests were collected
            failed.append(suite)

    print()
    if failed:
        print(f"FAILED: {', '.join(failed)}")
        return 1
    print(f"all {len(SUITES)} suites passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
