from fastapi import FastAPI

app = FastAPI(title="FalseTech Service")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
