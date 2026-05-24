from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_PATH = BACKEND_ROOT / ".env"


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), os.path.expandvars(value.strip()))


def main() -> int:
    parser = argparse.ArgumentParser(description="Check configured MySQL storage and Redis cache.")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_PATH)
    args = parser.parse_args()

    load_env_file(args.env_file)
    sys.path.insert(0, str(BACKEND_ROOT))

    from app import cache, storage

    result = {
        "storage": storage.status(),
        "cache": cache.status(),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    storage_ok = result["storage"].get("backend") == "mysql" and result["storage"].get("available") is True
    cache_ok = result["cache"].get("enabled") is True and result["cache"].get("available") is True
    return 0 if storage_ok and cache_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
