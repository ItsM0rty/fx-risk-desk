import argparse
import json
from pathlib import Path

from .api import app

SCHEMA = Path(__file__).resolve().parents[1] / "packages" / "client" / "openapi.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Export the deterministic FastAPI contract.")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    output = json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"
    if args.check:
        if SCHEMA.read_text(encoding="utf-8") != output:
            raise SystemExit("OpenAPI snapshot is stale. Export it before generating the client.")
    else:
        SCHEMA.write_text(output, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
