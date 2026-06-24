import argparse
import os
from pathlib import Path


def healthcheck() -> int:
    data_dir = Path(os.getenv("FALSETECH_WORKER_DATA_DIR", "/data"))
    config_path = Path(os.getenv("WORKER_CONFIG_PATH", "/config/worker.env"))

    if not data_dir.exists():
        print(f"Missing data dir: {data_dir}")
        return 1

    if config_path.exists() and not config_path.is_file():
        print(f"Config path is not a file: {config_path}")
        return 1

    print("status=ok")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--healthcheck", action="store_true")
    args = parser.parse_args()

    if args.healthcheck:
        return healthcheck()

    raise SystemExit("Worker runtime not implemented in this template.")


if __name__ == "__main__":
    raise SystemExit(main())
