from fastapi import FastAPI
from dotenv import load_dotenv

# Load environment variables from .env for local dev
load_dotenv()

from app.db import get_engine, db_ping  # noqa: E402

app = FastAPI(title="Blog Platform API", version="0.1.0")

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/readyz")
def readyz():
    engine = get_engine()
    db_ping(engine)
    return {"status": "ready", "db": "ok"}
