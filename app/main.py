from fastapi import FastAPI
import logging

from .api.routes import router as agent_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

app = FastAPI(title="Trading Bot Agent")

app.include_router(agent_router, prefix="/api/agent")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
