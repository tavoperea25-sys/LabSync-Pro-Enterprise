"""Casos de uso de la ficha técnica extendida, accesorios y manuales de un
equipo — Fase 2 de hojas de vida (docs/24-especificacion-hojas-de-vida-
mantenimiento-firmas.md, docs/25-diseno-tecnico-hojas-de-vida.md)."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field

from app.core.errors import ErrorDeDominio, RecursoNoEncontrado
from app.modules.equipos.application.equipo_service import EquipoNoEncontrado
from app.modules.equipos.domain.entities import (
    IDIOMAS_MANUAL,
    TIPOS_MANUAL,
    EquipoAccesorio,
    EquipoFichaTecnica,
    EquipoManual,
)
from app.modules.equipos.domain.ports import EquipoRepository
from app.modules.equipos.infrastructure.repositories import FichaTecnicaRepositorySQLAlchemy


class AccesorioNoEncontrado(RecursoNoEncontrado):
    def __init__(self) -> None:
        super().__init__("accesorio_no_encontrado", "El accesorio no existe.")


class DescripcionAccesorioObligatoria(ErrorDeDominio):
    def __init__(self) -> None:
        super().__init__(
            "descripcion_accesorio_obligatoria", "La descripción del accesorio es obligatoria."
        )


class CantidadInvalida(ErrorDeDominio):
    def __init__(self) -> None:
        super().__init__("cantidad_invalida", "La cantidad, si se indica, debe ser un entero mayor a cero.")


class TipoManualInvalido(ErrorDeDominio):
    def __init__(self, tipo: str) -> None:
        super().__init__(
            "tipo_manual_invalido",
            f"'{tipo}' no es un tipo de manual válido.",
            {"valores_permitidos": list(TIPOS_MANUAL)},
        )


class IdiomaManualInvalido(ErrorDeDominio):
    def __init__(self, idioma: str) -> None:
        super().__init__(
            "idioma_manual_invalido",
            f"'{idioma}' no es un idioma válido.",
            {"valores_permitidos": list(IDIOMAS_MANUAL)},
        )


@dataclass
class DatosFichaTecnica:
    # Todos opcionales — "ningún campo técnico obligatorio: todos admiten
    # vacío" (docs/24-...md sección 3.8).
    voltaje: str | None = None
    corriente: str | None = None
    frecuencia: str | None = None
    corriente_ma: str | None = None
    variable_medicion: str | None = None
    rango_medicion: str | None = None
    rpm: str | None = None
    temperatura_trabajo: str | None = None
    humedad_trabajo: str | None = None
    peso: str | None = None
    dimensiones: str | None = None
    color: str | None = None
    numero_puertas: str | None = None
    clase_sistema: str | None = None
    alimentacion: str | None = None
    uso: str | None = None
    uso_especifico: str | None = None
    condiciones_ambientales: str | None = None
    datos_adicionales: dict = field(default_factory=dict)


class FichaTecnicaService:
    """Agrupa ficha técnica (1:1), accesorios (1:N) y manuales (1:N, único
    por tipo) — las tres viven bajo el mismo equipo, mismo criterio de
    agrupación que `EquipoRepository.obtener_por_id()` usa como punto único
    de validación de existencia + aislamiento por tenant (RLS) antes de
    tocar cualquiera de las tres."""

    def __init__(self, equipos: EquipoRepository, ficha_tecnica: FichaTecnicaRepositorySQLAlchemy) -> None:
        self._equipos = equipos
        self._ficha_tecnica = ficha_tecnica

    def _validar_equipo(self, equipo_id: uuid.UUID):  # type: ignore[no-untyped-def]
        equipo = self._equipos.obtener_por_id(equipo_id)
        if equipo is None or not equipo.esta_activo():
            raise EquipoNoEncontrado()
        return equipo

    # ---- Ficha técnica (1:1) -------------------------------------------------

    def obtener_ficha_tecnica(self, equipo_id: uuid.UUID) -> EquipoFichaTecnica | None:
        self._validar_equipo(equipo_id)
        return self._ficha_tecnica.obtener_ficha_tecnica(equipo_id)

    def guardar_ficha_tecnica(self, equipo_id: uuid.UUID, datos: DatosFichaTecnica) -> EquipoFichaTecnica:
        equipo = self._validar_equipo(equipo_id)
        return self._ficha_tecnica.guardar_ficha_tecnica(equipo.laboratorio_id, equipo_id, asdict(datos))

    # ---- Accesorios (1:N) -----------------------------------------------------

    def listar_accesorios(self, equipo_id: uuid.UUID) -> list[EquipoAccesorio]:
        self._validar_equipo(equipo_id)
        return self._ficha_tecnica.listar_accesorios(equipo_id)

    def crear_accesorio(
        self, equipo_id: uuid.UUID, cantidad: int | None, descripcion: str, observaciones: str | None
    ) -> EquipoAccesorio:
        equipo = self._validar_equipo(equipo_id)
        self._validar_accesorio(cantidad, descripcion)
        return self._ficha_tecnica.crear_accesorio(
            equipo.laboratorio_id, equipo_id, cantidad, descripcion.strip(), observaciones
        )

    def actualizar_accesorio(
        self,
        equipo_id: uuid.UUID,
        accesorio_id: uuid.UUID,
        cantidad: int | None,
        descripcion: str,
        observaciones: str | None,
    ) -> EquipoAccesorio:
        self._validar_equipo(equipo_id)
        self._validar_accesorio(cantidad, descripcion)
        self._obtener_accesorio_del_equipo(equipo_id, accesorio_id)
        return self._ficha_tecnica.actualizar_accesorio(
            accesorio_id, cantidad, descripcion.strip(), observaciones
        )

    def eliminar_accesorio(self, equipo_id: uuid.UUID, accesorio_id: uuid.UUID) -> None:
        self._validar_equipo(equipo_id)
        self._obtener_accesorio_del_equipo(equipo_id, accesorio_id)
        self._ficha_tecnica.eliminar_accesorio(accesorio_id)

    def _obtener_accesorio_del_equipo(self, equipo_id: uuid.UUID, accesorio_id: uuid.UUID) -> EquipoAccesorio:
        accesorio = self._ficha_tecnica.obtener_accesorio(accesorio_id)
        if accesorio is None or accesorio.equipo_id != equipo_id:
            raise AccesorioNoEncontrado()
        return accesorio

    @staticmethod
    def _validar_accesorio(cantidad: int | None, descripcion: str) -> None:
        if not descripcion or not descripcion.strip():
            raise DescripcionAccesorioObligatoria()
        if cantidad is not None and cantidad <= 0:
            raise CantidadInvalida()

    # ---- Manuales (1:N, único por tipo) ----------------------------------------

    def listar_manuales(self, equipo_id: uuid.UUID) -> list[EquipoManual]:
        self._validar_equipo(equipo_id)
        return self._ficha_tecnica.listar_manuales(equipo_id)

    def guardar_manual(
        self,
        equipo_id: uuid.UUID,
        tipo: str,
        disponible: bool,
        idioma: str | None,
        object_key: str | None,
    ) -> EquipoManual:
        equipo = self._validar_equipo(equipo_id)
        if tipo not in TIPOS_MANUAL:
            raise TipoManualInvalido(tipo)
        if idioma is not None and idioma not in IDIOMAS_MANUAL:
            raise IdiomaManualInvalido(idioma)
        return self._ficha_tecnica.guardar_manual(
            equipo.laboratorio_id, equipo_id, tipo, disponible, idioma, object_key
        )
