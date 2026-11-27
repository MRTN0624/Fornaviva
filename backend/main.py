"""
main.py — Punto de entrada del backend de Fornaviva.

Arrancar en desarrollo:
    cd backend
    uvicorn main:app --reload --port 8000

Variables de entorno (ver .env.example):
    LLM_ENABLED     — true para habilitar Gemini (false por defecto)
    LLM_PROVIDER    — gemini (único proveedor implementado)
    LLM_API_KEY     — clave solo del backend; vacía activa el fallback
    LLM_MODEL_NAME  — gemini-3.5-flash-lite (modelo verificado; ver GEMINI.md)
"""

import os
import sys

# Añadir backend/ al path para que los imports relativos funcionen
# tanto ejecutando desde la raíz como desde backend/
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from request_limits import RequestSizeLimitMiddleware
from routes.chat import router as chat_router
from routes.data import router as data_router

app = FastAPI(
    title="Fornaviva API",
    description=(
        "Backend del chatbot y la web de Fornaviva, "
        "una pizzería ficticia creada como proyecto de demostración."
    ),
    version="1.0.0",
)

app.add_middleware(RequestSizeLimitMiddleware)

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:4173"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(chat_router, prefix="/api")
app.include_router(data_router, prefix="/api")


@app.get("/")
def root():
    return {
        "proyecto": "Fornaviva",
        "descripcion": "Pizzería ficticia — proyecto de demostración",
        "docs": "/docs",
    }
