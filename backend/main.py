## Keep runtime imports inside routers; avoid unused imports here.
from contextlib import asynccontextmanager

from api import router as api_router
from database.engine import ensure_tables
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_tables()
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return JSONResponse({"ok": True, "message": "API root"})


@app.get("/healthz")
def health():
    return JSONResponse({"ok": True, "message": "API is healthy"})


app.include_router(api_router, prefix="/api")
