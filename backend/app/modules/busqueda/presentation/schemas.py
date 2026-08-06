"""Schemas Pydantic del módulo Búsqueda Global. Ver docs/15-api-design.md."""

from __future__ import annotations

import uuid

from pydantic import BaseModel


class ResultadoBusqueda(BaseModel):
    tipo: str
    id: uuid.UUID
    titulo: str
    subtitulo: str | None
    ruta: str
