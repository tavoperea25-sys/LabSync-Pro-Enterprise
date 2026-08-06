import { apiFetch, apiFetchBlob } from "@/lib/httpClient";

import type {
  ActualizarUmbrales,
  Area,
  CategoriaEquipo,
  Configuracion,
  DatosCambiarPassword,
  DatosPerfilPropio,
  Institucion,
  MapeoEstadosMantenimiento,
  PerfilActualizado,
  PoliticaPassword,
  UrlSubidaLogo,
} from "../types";

export async function obtenerConfiguracion(): Promise<Configuracion> {
  return apiFetch<Configuracion>("/configuracion");
}

export async function actualizarUmbrales(datos: ActualizarUmbrales): Promise<Configuracion> {
  return apiFetch<Configuracion>("/configuracion/umbrales", { method: "PATCH", body: JSON.stringify(datos) });
}

export async function actualizarPoliticaPassword(politica: PoliticaPassword | null): Promise<Configuracion> {
  return apiFetch<Configuracion>("/configuracion/politica-password", {
    method: "PATCH",
    body: JSON.stringify({ politica_password: politica }),
  });
}

export async function actualizarMapeoEstadosMantenimiento(
  mapeo: MapeoEstadosMantenimiento | null,
): Promise<Configuracion> {
  return apiFetch<Configuracion>("/configuracion/mapeo-estados-mantenimiento", {
    method: "PATCH",
    body: JSON.stringify({ mapeo_estados_mantenimiento: mapeo }),
  });
}

export async function obtenerInstitucion(): Promise<Institucion> {
  return apiFetch<Institucion>("/configuracion/institucion");
}

export async function actualizarInstitucion(nombre: string, logoObjectKey: string | null): Promise<Institucion> {
  return apiFetch<Institucion>("/configuracion/institucion", {
    method: "PATCH",
    body: JSON.stringify({ nombre, logo_object_key: logoObjectKey }),
  });
}

export async function solicitarUrlLogo(
  nombreArchivo: string,
  tipoMime: string,
  tamanoBytes: number,
): Promise<UrlSubidaLogo> {
  return apiFetch<UrlSubidaLogo>("/configuracion/institucion/logo-upload-url", {
    method: "POST",
    body: JSON.stringify({ nombre_archivo: nombreArchivo, tipo_mime: tipoMime, tamano_bytes: tamanoBytes }),
  });
}

export async function listarCategorias(): Promise<CategoriaEquipo[]> {
  return apiFetch<CategoriaEquipo[]>("/categorias-equipo");
}

export async function crearCategoria(
  nombre: string,
  frecuenciaMeses: number | null,
  bloqueaActivacionSiCalibracionVencida: boolean,
): Promise<CategoriaEquipo> {
  return apiFetch<CategoriaEquipo>("/categorias-equipo", {
    method: "POST",
    body: JSON.stringify({
      nombre,
      frecuencia_calibracion_default_meses: frecuenciaMeses,
      bloquea_activacion_si_calibracion_vencida: bloqueaActivacionSiCalibracionVencida,
    }),
  });
}

export async function actualizarCategoria(
  id: string,
  nombre: string,
  frecuenciaMeses: number | null,
  bloqueaActivacionSiCalibracionVencida: boolean,
): Promise<CategoriaEquipo> {
  return apiFetch<CategoriaEquipo>(`/categorias-equipo/${id}`, {
    method: "PATCH",
    body: JSON.stringify({
      nombre,
      frecuencia_calibracion_default_meses: frecuenciaMeses,
      bloquea_activacion_si_calibracion_vencida: bloqueaActivacionSiCalibracionVencida,
    }),
  });
}

export async function eliminarCategoria(id: string): Promise<void> {
  await apiFetch<void>(`/categorias-equipo/${id}`, { method: "DELETE" });
}

export async function listarAreas(): Promise<Area[]> {
  return apiFetch<Area[]>("/areas");
}

export async function crearArea(nombre: string): Promise<Area> {
  return apiFetch<Area>("/areas", { method: "POST", body: JSON.stringify({ nombre }) });
}

export async function actualizarArea(id: string, nombre: string): Promise<Area> {
  return apiFetch<Area>(`/areas/${id}`, { method: "PATCH", body: JSON.stringify({ nombre }) });
}

export async function eliminarArea(id: string): Promise<void> {
  await apiFetch<void>(`/areas/${id}`, { method: "DELETE" });
}

export async function actualizarPerfilPropio(datos: DatosPerfilPropio): Promise<PerfilActualizado> {
  return apiFetch<PerfilActualizado>("/usuarios/me", { method: "PATCH", body: JSON.stringify(datos) });
}

export async function solicitarUrlFotoPerfil(
  nombreArchivo: string,
  tipoMime: string,
  tamanoBytes: number,
): Promise<UrlSubidaLogo> {
  return apiFetch<UrlSubidaLogo>("/usuarios/me/upload-url/foto", {
    method: "POST",
    body: JSON.stringify({ nombre_archivo: nombreArchivo, tipo_mime: tipoMime, tamano_bytes: tamanoBytes }),
  });
}

export async function cambiarPasswordPropio(datos: DatosCambiarPassword): Promise<void> {
  await apiFetch<void>("/usuarios/me/cambiar-password", { method: "POST", body: JSON.stringify(datos) });
}

export async function exportarDatosTenant(): Promise<Blob> {
  return apiFetchBlob("/configuracion/exportar-datos");
}
