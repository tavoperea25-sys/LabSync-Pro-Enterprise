"""Política de complejidad de contraseña — RF-USR-05, RF-CFG-03.

Política fija por defecto (longitud mínima + mayúscula + minúscula + dígito
+ símbolo), configurable desde el Sprint 12 vía `configuraciones_laboratorio
.politica_password_json` (módulo Configuración) — un laboratorio que nunca
configuró nada sigue operando exactamente con estos valores por defecto."""

from __future__ import annotations

import re
from typing import Any

from app.core.errors import ErrorDeDominio

LONGITUD_MINIMA = 10


class PasswordNoCumplePolitica(ErrorDeDominio):
    def __init__(self, motivos: list[str]) -> None:
        super().__init__(
            "password_no_cumple_politica",
            "La contraseña no cumple la política de complejidad.",
            {"motivos": motivos},
        )


def validar_password(password: str, politica: dict[str, Any] | None = None) -> None:
    politica = politica or {}
    longitud_minima = politica.get("longitud_minima", LONGITUD_MINIMA)
    motivos = []
    if len(password) < longitud_minima:
        motivos.append(f"Debe tener al menos {longitud_minima} caracteres.")
    if politica.get("requiere_mayuscula", True) and not re.search(r"[A-Z]", password):
        motivos.append("Debe incluir al menos una letra mayúscula.")
    if politica.get("requiere_minuscula", True) and not re.search(r"[a-z]", password):
        motivos.append("Debe incluir al menos una letra minúscula.")
    if politica.get("requiere_digito", True) and not re.search(r"\d", password):
        motivos.append("Debe incluir al menos un dígito.")
    if politica.get("requiere_simbolo", True) and not re.search(r"[^\w\s]", password):
        motivos.append("Debe incluir al menos un símbolo.")
    if motivos:
        raise PasswordNoCumplePolitica(motivos)
