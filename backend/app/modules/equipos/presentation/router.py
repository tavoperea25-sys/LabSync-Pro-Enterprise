"""Endpoints de Equipos. Ver docs/15-api-design.md."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.almacenamiento_minio import AlmacenamientoMinIO
from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import ErrorDeDominio
from app.core.ip import ip_valida
from app.modules.auditoria.infrastructure.repositories import AuditoriaRepositorySQLAlchemy
from app.modules.auth.presentation.dependencies import UsuarioContexto, requiere_permiso
from app.modules.equipos.application.equipo_service import ActorContexto, DatosEquipo, EquipoService
from app.modules.equipos.application.ficha_tecnica_service import DatosFichaTecnica, FichaTecnicaService
from app.modules.equipos.application.referencia_service import ActorContexto as ActorReferencia
from app.modules.equipos.application.referencia_service import ReferenciaService
from app.modules.equipos.domain.ports import FiltrosEquipo
from app.modules.equipos.infrastructure.exportador import generar_excel
from app.modules.equipos.infrastructure.repositories import (
    AreaRepositorySQLAlchemy,
    CategoriaEquipoRepositorySQLAlchemy,
    EquipoRepositorySQLAlchemy,
    FabricanteRepositorySQLAlchemy,
    FichaTecnicaRepositorySQLAlchemy,
    ProveedorRepositorySQLAlchemy,
)
from app.modules.equipos.presentation.schemas import (
    AccesorioOut,
    AccesorioRequest,
    AreaOut,
    AreaRequest,
    CategoriaEquipoOut,
    CategoriaEquipoRequest,
    EquipoOut,
    EquipoRequest,
    FabricanteOut,
    FabricanteRequest,
    FichaTecnicaOut,
    FichaTecnicaRequest,
    HistorialEntradaOut,
    ManualOut,
    ManualRequest,
    PaginaEquiposOut,
    ProveedorOut,
    ProveedorRequest,
    UrlFotoOut,
    UrlFotoRequest,
    UrlManualOut,
    UrlManualRequest,
)
from app.modules.qr.application.qr_service import QrService
from app.modules.qr.infrastructure.repositories import (
    IncidenciaQrRepositorySQLAlchemy,
    QrTokenRepositorySQLAlchemy,
)

router = APIRouter(prefix="/api/v1", tags=["equipos"])

_almacenamiento_fotos = AlmacenamientoMinIO(get_settings().minio_bucket_fotos_equipos)
_almacenamiento_manuales = AlmacenamientoMinIO(get_settings().minio_bucket_manuales_equipos)


def _service(db: Session) -> EquipoService:
    return EquipoService(
        EquipoRepositorySQLAlchemy(db),
        AuditoriaRepositorySQLAlchemy(db),
        ProveedorRepositorySQLAlchemy(db),
        FabricanteRepositorySQLAlchemy(db),
        FichaTecnicaRepositorySQLAlchemy(db),
        _almacenamiento_fotos,
        _almacenamiento_manuales,
    )


def _ficha_tecnica_service(db: Session) -> FichaTecnicaService:
    return FichaTecnicaService(EquipoRepositorySQLAlchemy(db), FichaTecnicaRepositorySQLAlchemy(db))


def _generar_qr(db: Session, laboratorio_id: uuid.UUID, equipo_id: uuid.UUID) -> None:
    """RF-QR-01 — todo equipo nuevo recibe su QR automáticamente, incluidas
    las copias creadas por RF-EQ-05 (duplicar)."""
    qr_service = QrService(
        QrTokenRepositorySQLAlchemy(db), IncidenciaQrRepositorySQLAlchemy(db), EquipoRepositorySQLAlchemy(db)
    )
    qr_service.generar_para_equipo(laboratorio_id, equipo_id)


def _actor(request: Request, usuario: UsuarioContexto) -> ActorContexto:
    return ActorContexto(
        usuario_id=usuario.id, ip_origen=ip_valida(request.client.host if request.client else None)
    )


def _a_out(equipo, service: EquipoService) -> EquipoOut:  # type: ignore[no-untyped-def]
    return EquipoOut(
        id=equipo.id,
        codigo_interno=equipo.codigo_interno,
        nombre=equipo.nombre,
        estado_operativo=equipo.estado_operativo,
        categoria_id=equipo.categoria_id,
        area_id=equipo.area_id,
        responsable_id=equipo.responsable_id,
        marca=equipo.marca,
        modelo=equipo.modelo,
        numero_serie=equipo.numero_serie,
        fabricante=equipo.fabricante,
        proveedor=equipo.proveedor,
        fecha_adquisicion=equipo.fecha_adquisicion,
        observaciones=equipo.observaciones,
        foto_url=service.url_foto(equipo),
        foto_object_key=equipo.foto_object_key,
        manual_url=service.url_manual(equipo),
        manual_object_key=equipo.manual_object_key,
        proveedor_id=equipo.proveedor_id,
        fabricante_id=equipo.fabricante_id,
        capitulo=equipo.capitulo,
        grupo=equipo.grupo,
        subgrupo=equipo.subgrupo,
        ubicacion=equipo.ubicacion,
        numero_inventario=equipo.numero_inventario,
        condicion_fisica=equipo.condicion_fisica,
        clasificacion_riesgo=equipo.clasificacion_riesgo,
        criticidad=equipo.criticidad,
        forma_adquisicion=equipo.forma_adquisicion,
        garantia=equipo.garantia,
        garantia_inicio=equipo.garantia_inicio,
        garantia_fin=equipo.garantia_fin,
        creado_en=equipo.creado_en,
        actualizado_en=equipo.actualizado_en,
    )


def _a_datos(datos: EquipoRequest) -> DatosEquipo:
    return DatosEquipo(**datos.model_dump())


@router.get("/equipos", response_model=PaginaEquiposOut)
def listar_equipos(
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer")),
    q: str | None = Query(default=None),
    categoria_id: uuid.UUID | None = Query(default=None),
    area_id: uuid.UUID | None = Query(default=None),
    estado_operativo: str | None = Query(default=None),
    pagina: int = Query(default=1, ge=1),
    tamano_pagina: int = Query(default=20, ge=1, le=100),
) -> PaginaEquiposOut:
    service = _service(db)
    resultado = service.listar(
        FiltrosEquipo(
            q=q,
            categoria_id=categoria_id,
            area_id=area_id,
            estado_operativo=estado_operativo,
            pagina=pagina,
            tamano_pagina=tamano_pagina,
        )
    )
    return PaginaEquiposOut(
        items=[_a_out(e, service) for e in resultado.items],
        total=resultado.total,
        pagina=resultado.pagina,
        tamano_pagina=resultado.tamano_pagina,
    )


@router.post("/equipos", response_model=EquipoOut, status_code=201)
def crear_equipo(
    datos: EquipoRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("equipos.crear")),
) -> EquipoOut:
    service = _service(db)
    equipo = service.crear(usuario.laboratorio_id, _a_datos(datos), _actor(request, usuario))
    _generar_qr(db, usuario.laboratorio_id, equipo.id)
    db.commit()
    return _a_out(equipo, service)


@router.post("/equipos/upload-url/foto", response_model=UrlFotoOut)
def solicitar_url_foto(
    datos: UrlFotoRequest,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.crear")),
) -> UrlFotoOut:
    url, object_key = _service(db).solicitar_url_foto(
        datos.nombre_archivo, datos.tipo_mime, datos.tamano_bytes
    )
    return UrlFotoOut(url_subida=url, object_key=object_key)


@router.post("/equipos/upload-url/manual", response_model=UrlManualOut)
def solicitar_url_manual(
    datos: UrlManualRequest,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.crear")),
) -> UrlManualOut:
    url, object_key = _service(db).solicitar_url_manual(
        datos.nombre_archivo, datos.tipo_mime, datos.tamano_bytes
    )
    return UrlManualOut(url_subida=url, object_key=object_key)


@router.get("/equipos/export")
def exportar_equipos(
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer")),
    formato: str = Query(default="xlsx"),
    q: str | None = Query(default=None),
    categoria_id: uuid.UUID | None = Query(default=None),
    area_id: uuid.UUID | None = Query(default=None),
    estado_operativo: str | None = Query(default=None),
) -> StreamingResponse:
    if formato != "xlsx":
        raise ErrorDeDominio(
            "formato_no_soportado",
            "Por ahora solo se puede exportar a Excel (.xlsx); PDF corporativo llega con Reportes.",
            {"formatos_disponibles": ["xlsx"]},
        )

    equipos = EquipoRepositorySQLAlchemy(db).listar_todos(
        FiltrosEquipo(q=q, categoria_id=categoria_id, area_id=area_id, estado_operativo=estado_operativo)
    )
    contenido = generar_excel(equipos)
    return StreamingResponse(
        iter([contenido]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=equipos.xlsx"},
    )


@router.get("/equipos/{equipo_id}", response_model=EquipoOut)
def obtener_equipo(
    equipo_id: uuid.UUID,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer")),
) -> EquipoOut:
    service = _service(db)
    return _a_out(service.obtener(equipo_id), service)


@router.patch("/equipos/{equipo_id}", response_model=EquipoOut)
def actualizar_equipo(
    equipo_id: uuid.UUID,
    datos: EquipoRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("equipos.crear")),
) -> EquipoOut:
    service = _service(db)
    equipo = service.actualizar(equipo_id, _a_datos(datos), _actor(request, usuario))
    db.commit()
    return _a_out(equipo, service)


@router.delete("/equipos/{equipo_id}", status_code=204, response_model=None)
def eliminar_equipo(
    equipo_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("equipos.crear")),
) -> None:
    _service(db).eliminar(equipo_id, _actor(request, usuario))
    db.commit()


@router.post("/equipos/{equipo_id}/duplicar", response_model=EquipoOut, status_code=201)
def duplicar_equipo(
    equipo_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("equipos.crear")),
) -> EquipoOut:
    service = _service(db)
    equipo = service.duplicar(equipo_id, _actor(request, usuario))
    _generar_qr(db, usuario.laboratorio_id, equipo.id)
    db.commit()
    return _a_out(equipo, service)


@router.get("/equipos/{equipo_id}/historial", response_model=list[HistorialEntradaOut])
def historial_equipo(
    equipo_id: uuid.UUID,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer")),
) -> list[HistorialEntradaOut]:
    entradas = _service(db).historial(equipo_id)
    return [
        HistorialEntradaOut(
            id=e.id,
            usuario_id=e.usuario_id,
            accion=e.accion,
            valor_anterior=e.valor_anterior,
            valor_nuevo=e.valor_nuevo,
            creado_en=e.creado_en,
        )
        for e in entradas
    ]


def _referencia_service(db: Session) -> ReferenciaService:
    return ReferenciaService(
        CategoriaEquipoRepositorySQLAlchemy(db),
        AreaRepositorySQLAlchemy(db),
        EquipoRepositorySQLAlchemy(db),
        AuditoriaRepositorySQLAlchemy(db),
        ProveedorRepositorySQLAlchemy(db),
        FabricanteRepositorySQLAlchemy(db),
    )


def _actor_referencia(request: Request, usuario: UsuarioContexto) -> ActorReferencia:
    return ActorReferencia(
        usuario_id=usuario.id, ip_origen=ip_valida(request.client.host if request.client else None)
    )


def _categoria_a_out(fila) -> CategoriaEquipoOut:  # type: ignore[no-untyped-def]
    return CategoriaEquipoOut(
        id=fila.id,
        nombre=fila.nombre,
        frecuencia_calibracion_default_meses=fila.frecuencia_calibracion_default_meses,
        bloquea_activacion_si_calibracion_vencida=fila.bloquea_activacion_si_calibracion_vencida,
    )


@router.get("/categorias-equipo", response_model=list[CategoriaEquipoOut])
def listar_categorias(
    db: Session = Depends(get_db), _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer"))
) -> list[CategoriaEquipoOut]:
    return [_categoria_a_out(f) for f in CategoriaEquipoRepositorySQLAlchemy(db).listar()]


@router.post("/categorias-equipo", response_model=CategoriaEquipoOut, status_code=201)
def crear_categoria(
    datos: CategoriaEquipoRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("configuracion.gestionar")),
) -> CategoriaEquipoOut:
    fila = _referencia_service(db).crear_categoria(
        usuario.laboratorio_id,
        _actor_referencia(request, usuario),
        datos.nombre,
        datos.frecuencia_calibracion_default_meses,
        datos.bloquea_activacion_si_calibracion_vencida,
    )
    db.commit()
    return _categoria_a_out(fila)


@router.patch("/categorias-equipo/{categoria_id}", response_model=CategoriaEquipoOut)
def actualizar_categoria(
    categoria_id: uuid.UUID,
    datos: CategoriaEquipoRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("configuracion.gestionar")),
) -> CategoriaEquipoOut:
    fila = _referencia_service(db).actualizar_categoria(
        usuario.laboratorio_id,
        _actor_referencia(request, usuario),
        categoria_id,
        datos.nombre,
        datos.frecuencia_calibracion_default_meses,
        datos.bloquea_activacion_si_calibracion_vencida,
    )
    db.commit()
    return _categoria_a_out(fila)


@router.delete("/categorias-equipo/{categoria_id}", status_code=204, response_model=None)
def eliminar_categoria(
    categoria_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("configuracion.gestionar")),
) -> None:
    _referencia_service(db).eliminar_categoria(
        usuario.laboratorio_id, _actor_referencia(request, usuario), categoria_id
    )
    db.commit()


@router.get("/areas", response_model=list[AreaOut])
def listar_areas(
    db: Session = Depends(get_db), _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer"))
) -> list[AreaOut]:
    filas = AreaRepositorySQLAlchemy(db).listar()
    return [AreaOut(id=f.id, nombre=f.nombre) for f in filas]


@router.post("/areas", response_model=AreaOut, status_code=201)
def crear_area(
    datos: AreaRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("configuracion.gestionar")),
) -> AreaOut:
    fila = _referencia_service(db).crear_area(
        usuario.laboratorio_id, _actor_referencia(request, usuario), datos.nombre
    )
    db.commit()
    return AreaOut(id=fila.id, nombre=fila.nombre)


@router.patch("/areas/{area_id}", response_model=AreaOut)
def actualizar_area(
    area_id: uuid.UUID,
    datos: AreaRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("configuracion.gestionar")),
) -> AreaOut:
    fila = _referencia_service(db).actualizar_area(
        usuario.laboratorio_id, _actor_referencia(request, usuario), area_id, datos.nombre
    )
    db.commit()
    return AreaOut(id=fila.id, nombre=fila.nombre)


@router.delete("/areas/{area_id}", status_code=204, response_model=None)
def eliminar_area(
    area_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("configuracion.gestionar")),
) -> None:
    _referencia_service(db).eliminar_area(
        usuario.laboratorio_id, _actor_referencia(request, usuario), area_id
    )
    db.commit()


# ---- Catálogos de proveedores y fabricantes (Fase 2 de hojas de vida) ---------


def _proveedor_a_out(fila) -> ProveedorOut:  # type: ignore[no-untyped-def]
    return ProveedorOut(
        id=fila.id,
        nombre=fila.nombre,
        pais_ciudad=fila.pais_ciudad,
        direccion=fila.direccion,
        email=fila.email,
        telefono=fila.telefono,
        contacto=fila.contacto,
    )


def _fabricante_a_out(fila) -> FabricanteOut:  # type: ignore[no-untyped-def]
    return FabricanteOut(
        id=fila.id,
        nombre=fila.nombre,
        pais_ciudad=fila.pais_ciudad,
        direccion=fila.direccion,
        email=fila.email,
        telefono=fila.telefono,
        contacto=fila.contacto,
    )


@router.get("/proveedores", response_model=list[ProveedorOut])
def listar_proveedores(
    db: Session = Depends(get_db), _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer"))
) -> list[ProveedorOut]:
    return [_proveedor_a_out(f) for f in ProveedorRepositorySQLAlchemy(db).listar()]


@router.post("/proveedores", response_model=ProveedorOut, status_code=201)
def crear_proveedor(
    datos: ProveedorRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("configuracion.gestionar")),
) -> ProveedorOut:
    fila = _referencia_service(db).crear_proveedor(
        usuario.laboratorio_id, _actor_referencia(request, usuario), **datos.model_dump()
    )
    db.commit()
    return _proveedor_a_out(fila)


@router.patch("/proveedores/{proveedor_id}", response_model=ProveedorOut)
def actualizar_proveedor(
    proveedor_id: uuid.UUID,
    datos: ProveedorRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("configuracion.gestionar")),
) -> ProveedorOut:
    fila = _referencia_service(db).actualizar_proveedor(
        usuario.laboratorio_id, _actor_referencia(request, usuario), proveedor_id, **datos.model_dump()
    )
    db.commit()
    return _proveedor_a_out(fila)


@router.delete("/proveedores/{proveedor_id}", status_code=204, response_model=None)
def eliminar_proveedor(
    proveedor_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("configuracion.gestionar")),
) -> None:
    _referencia_service(db).eliminar_proveedor(
        usuario.laboratorio_id, _actor_referencia(request, usuario), proveedor_id
    )
    db.commit()


@router.get("/fabricantes", response_model=list[FabricanteOut])
def listar_fabricantes(
    db: Session = Depends(get_db), _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer"))
) -> list[FabricanteOut]:
    return [_fabricante_a_out(f) for f in FabricanteRepositorySQLAlchemy(db).listar()]


@router.post("/fabricantes", response_model=FabricanteOut, status_code=201)
def crear_fabricante(
    datos: FabricanteRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("configuracion.gestionar")),
) -> FabricanteOut:
    fila = _referencia_service(db).crear_fabricante(
        usuario.laboratorio_id, _actor_referencia(request, usuario), **datos.model_dump()
    )
    db.commit()
    return _fabricante_a_out(fila)


@router.patch("/fabricantes/{fabricante_id}", response_model=FabricanteOut)
def actualizar_fabricante(
    fabricante_id: uuid.UUID,
    datos: FabricanteRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("configuracion.gestionar")),
) -> FabricanteOut:
    fila = _referencia_service(db).actualizar_fabricante(
        usuario.laboratorio_id, _actor_referencia(request, usuario), fabricante_id, **datos.model_dump()
    )
    db.commit()
    return _fabricante_a_out(fila)


@router.delete("/fabricantes/{fabricante_id}", status_code=204, response_model=None)
def eliminar_fabricante(
    fabricante_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("configuracion.gestionar")),
) -> None:
    _referencia_service(db).eliminar_fabricante(
        usuario.laboratorio_id, _actor_referencia(request, usuario), fabricante_id
    )
    db.commit()


# ---- Ficha técnica extendida, accesorios y manuales ---------------------------


def _ficha_tecnica_a_out(ficha) -> FichaTecnicaOut:  # type: ignore[no-untyped-def]
    return FichaTecnicaOut(
        voltaje=ficha.voltaje,
        corriente=ficha.corriente,
        frecuencia=ficha.frecuencia,
        corriente_ma=ficha.corriente_ma,
        variable_medicion=ficha.variable_medicion,
        rango_medicion=ficha.rango_medicion,
        rpm=ficha.rpm,
        temperatura_trabajo=ficha.temperatura_trabajo,
        humedad_trabajo=ficha.humedad_trabajo,
        peso=ficha.peso,
        dimensiones=ficha.dimensiones,
        color=ficha.color,
        numero_puertas=ficha.numero_puertas,
        clase_sistema=ficha.clase_sistema,
        alimentacion=ficha.alimentacion,
        uso=ficha.uso,
        uso_especifico=ficha.uso_especifico,
        condiciones_ambientales=ficha.condiciones_ambientales,
        datos_adicionales=ficha.datos_adicionales,
        actualizado_en=ficha.actualizado_en,
    )


_FICHA_TECNICA_VACIA = FichaTecnicaOut(
    voltaje=None,
    corriente=None,
    frecuencia=None,
    corriente_ma=None,
    variable_medicion=None,
    rango_medicion=None,
    rpm=None,
    temperatura_trabajo=None,
    humedad_trabajo=None,
    peso=None,
    dimensiones=None,
    color=None,
    numero_puertas=None,
    clase_sistema=None,
    alimentacion=None,
    uso=None,
    uso_especifico=None,
    condiciones_ambientales=None,
    datos_adicionales={},
    actualizado_en=None,
)


@router.get("/equipos/{equipo_id}/ficha-tecnica", response_model=FichaTecnicaOut)
def obtener_ficha_tecnica(
    equipo_id: uuid.UUID,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer")),
) -> FichaTecnicaOut:
    ficha = _ficha_tecnica_service(db).obtener_ficha_tecnica(equipo_id)
    return _ficha_tecnica_a_out(ficha) if ficha is not None else _FICHA_TECNICA_VACIA


@router.put("/equipos/{equipo_id}/ficha-tecnica", response_model=FichaTecnicaOut)
def guardar_ficha_tecnica(
    equipo_id: uuid.UUID,
    datos: FichaTecnicaRequest,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.crear")),
) -> FichaTecnicaOut:
    ficha = _ficha_tecnica_service(db).guardar_ficha_tecnica(
        equipo_id, DatosFichaTecnica(**datos.model_dump())
    )
    db.commit()
    return _ficha_tecnica_a_out(ficha)


def _accesorio_a_out(fila) -> AccesorioOut:  # type: ignore[no-untyped-def]
    return AccesorioOut(
        id=fila.id, cantidad=fila.cantidad, descripcion=fila.descripcion, observaciones=fila.observaciones
    )


@router.get("/equipos/{equipo_id}/accesorios", response_model=list[AccesorioOut])
def listar_accesorios(
    equipo_id: uuid.UUID,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer")),
) -> list[AccesorioOut]:
    return [_accesorio_a_out(f) for f in _ficha_tecnica_service(db).listar_accesorios(equipo_id)]


@router.post("/equipos/{equipo_id}/accesorios", response_model=AccesorioOut, status_code=201)
def crear_accesorio(
    equipo_id: uuid.UUID,
    datos: AccesorioRequest,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.crear")),
) -> AccesorioOut:
    fila = _ficha_tecnica_service(db).crear_accesorio(
        equipo_id, datos.cantidad, datos.descripcion, datos.observaciones
    )
    db.commit()
    return _accesorio_a_out(fila)


@router.patch("/equipos/{equipo_id}/accesorios/{accesorio_id}", response_model=AccesorioOut)
def actualizar_accesorio(
    equipo_id: uuid.UUID,
    accesorio_id: uuid.UUID,
    datos: AccesorioRequest,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.crear")),
) -> AccesorioOut:
    fila = _ficha_tecnica_service(db).actualizar_accesorio(
        equipo_id, accesorio_id, datos.cantidad, datos.descripcion, datos.observaciones
    )
    db.commit()
    return _accesorio_a_out(fila)


@router.delete("/equipos/{equipo_id}/accesorios/{accesorio_id}", status_code=204, response_model=None)
def eliminar_accesorio(
    equipo_id: uuid.UUID,
    accesorio_id: uuid.UUID,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.crear")),
) -> None:
    _ficha_tecnica_service(db).eliminar_accesorio(equipo_id, accesorio_id)
    db.commit()


def _manual_a_out(fila) -> ManualOut:  # type: ignore[no-untyped-def]
    url = None
    if fila.object_key is not None:
        url = _almacenamiento_manuales.url_descarga(fila.object_key, f"manual-{fila.tipo}.pdf")
    return ManualOut(
        tipo=fila.tipo, disponible=fila.disponible, idioma=fila.idioma, object_key=fila.object_key, url=url
    )


@router.get("/equipos/{equipo_id}/manuales", response_model=list[ManualOut])
def listar_manuales(
    equipo_id: uuid.UUID,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer")),
) -> list[ManualOut]:
    return [_manual_a_out(f) for f in _ficha_tecnica_service(db).listar_manuales(equipo_id)]


@router.put("/equipos/{equipo_id}/manuales/{tipo}", response_model=ManualOut)
def guardar_manual(
    equipo_id: uuid.UUID,
    tipo: str,
    datos: ManualRequest,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.crear")),
) -> ManualOut:
    fila = _ficha_tecnica_service(db).guardar_manual(
        equipo_id, tipo, datos.disponible, datos.idioma, datos.object_key
    )
    db.commit()
    return _manual_a_out(fila)
