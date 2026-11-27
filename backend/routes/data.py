"""
data.py — Endpoints GET de datos estáticos de Fornaviva.

GET /api/menu      → carta completa (menu.json)
GET /api/horarios  → horarios semanales (horarios.json)
GET /api/alergenos → alérgenos por plato (alergenos.json)
GET /api/faqs      → preguntas frecuentes (faqs.json)

Estos endpoints no dependen del LLM y funcionan siempre.
"""

from fastapi import APIRouter, HTTPException
from chatbot.respuestas import cargar_json

router = APIRouter()


@router.get("/menu")
def get_menu():
    datos = cargar_json("menu.json")
    if datos is None:
        raise HTTPException(status_code=503, detail="No se pudo cargar menu.json")
    return datos


@router.get("/horarios")
def get_horarios():
    datos = cargar_json("horarios.json")
    if datos is None:
        raise HTTPException(status_code=503, detail="No se pudo cargar horarios.json")
    return datos


@router.get("/alergenos")
def get_alergenos():
    datos = cargar_json("alergenos.json")
    if datos is None:
        raise HTTPException(status_code=503, detail="No se pudo cargar alergenos.json")
    return datos


@router.get("/faqs")
def get_faqs():
    datos = cargar_json("faqs.json")
    if datos is None:
        raise HTTPException(status_code=503, detail="No se pudo cargar faqs.json")
    return datos
