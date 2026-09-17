from fastapi import FastAPI

app = FastAPI(title="CivicPulse")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
