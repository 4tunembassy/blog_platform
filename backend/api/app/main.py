from fastapi import FastAPI

app = FastAPI(title="Governed Blog Platform API", version="0.1.0")

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/readyz")
def readyz():
    # In MVP we simply return ok. Later: check DB connectivity, queue connectivity.
    return {"ready": True}
