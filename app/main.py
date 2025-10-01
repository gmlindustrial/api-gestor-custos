from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import api_router

app = FastAPI(
    title="GMX - Módulo de Custos de Obras",
    description="Sistema de gestão de custos de construção para GMX",
    version="1.0.0"
)

# FRONTEND ORIGINS
origins = [
    "http://localhost:8080",                  # React local
    "https://gestor-custos.gmxindustrial.com.br",  # produção
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,      # necessário para cookies ou headers auth
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "GMX - Módulo de Custos de Obras API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
