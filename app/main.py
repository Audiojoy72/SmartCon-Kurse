"""SmartCon-Schulungen — FastAPI-Hauptmodul.

Start: .venv/bin/python -m app.main  →  http://localhost:8710
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config, preflight

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"

app = FastAPI(title="SmartCon-Schulungen", version="0.1.0")


@app.get("/api/preflight")
def api_preflight():
    """Preflight-Ampel: alle Abhängigkeiten prüfen (live, dauert wenige Sekunden)."""
    return {"checks": preflight.run_all(config.load())}


@app.get("/api/config")
def api_config_get():
    return config.load()


@app.post("/api/config")
async def api_config_post(cfg: dict):
    return config.save(cfg)


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")


def main():
    import uvicorn

    cfg = config.load()
    uvicorn.run(app, host="127.0.0.1", port=cfg["port"])


if __name__ == "__main__":
    main()
