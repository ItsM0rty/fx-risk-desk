import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
from tempfile import TemporaryDirectory
from threading import Thread
from time import monotonic, sleep

import uvicorn

from riskdesk.api import app

ROOT = Path(__file__).resolve().parents[1]
CLIENT_SMOKE_TEST = '''
import assert from "node:assert/strict";

const [packageName, baseUrl] = process.argv.slice(1);
const { createRiskDeskClient } = await import(packageName);
const client = createRiskDeskClient(baseUrl);

const { data, error, response } = await client.GET("/api/v1/runs/latest/risk", {
  params: { query: { hedge_pct: "50", limit: 1 } },
});

assert.equal(response.status, 200);
assert.equal(error, undefined);
assert.equal(data.run_id, "client-smoke");
assert.equal(data.hedge_pct, 50);
assert.deepEqual(data.points.map(point => point.date), ["2025-12-31"]);
'''


def smoke_test(package_name: str, directory: Path) -> None:
    point = {"pnl": -100, "unhedged_pnl": -250, "var": 200, "es": 230, "breach": False}
    snapshot = {
        "summary": {"run_id": "client-smoke"},
        "risk_series": {
            "50": [
                {**point, "date": "2025-12-30"},
                {**point, "date": "2025-12-31"},
            ],
        },
    }
    snapshot_file = directory / "risk.json"
    snapshot_file.write_text(json.dumps(snapshot), encoding="utf-8")
    os.environ["FX_RISK_RUN"] = str(snapshot_file)

    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, log_level="warning", lifespan="off"))
        thread = Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        try:
            deadline = monotonic() + 10
            while not server.started and thread.is_alive() and monotonic() < deadline:
                sleep(0.05)
            if not server.started:
                raise RuntimeError("FastAPI did not start for the client smoke test.")
            subprocess.run(
                ["node", "--input-type=module", "--eval", CLIENT_SMOKE_TEST,
                 package_name, f"http://127.0.0.1:{port}"],
                cwd=directory,
                check=True,
                timeout=15,
            )
        finally:
            server.should_exit = True
            thread.join(timeout=5)


def main() -> None:
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if npm is None:
        raise SystemExit("npm is required to check the client package.")

    with TemporaryDirectory(prefix="fx-risk-client-") as scratch:
        directory = Path(scratch)
        result = subprocess.run(
            [npm, "pack", "--workspace", "packages/client", "--ignore-scripts", "--json",
             "--pack-destination", str(directory)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        [packed] = json.loads(result.stdout)
        expected = {"LICENSE", "dist/index.js", "dist/index.d.ts", "dist/schema.d.ts"}
        missing = expected - {file["path"] for file in packed["files"]}
        if missing:
            raise SystemExit(f"Client archive is missing: {', '.join(sorted(missing))}")

        subprocess.run(
            [npm, "install", "--ignore-scripts", "--no-audit", "--no-fund", "--no-package-lock",
             str(directory / packed["filename"])],
            cwd=directory,
            check=True,
        )
        smoke_test(packed["name"], directory)
        print(f"{packed['id']} passed the installed-client FastAPI smoke test.")


if __name__ == "__main__":
    main()
