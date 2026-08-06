import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as api from "../api/mantenimientosApi";
import type { ArchivoConfirmado, DatosCierre, DatosMantenimiento } from "../types";

const CLAVE = "mantenimientos";

/** El historial de una ficha de equipo trae todo en una sola página (ver
 * default de `tamano_pagina` en el backend) — se desenvuelve `.items` acá
 * para que los consumidores existentes no tengan que saber de paginación. */
export function useMantenimientosPorEquipo(equipoId: string | undefined) {
  return useQuery({
    queryKey: [CLAVE, "equipo", equipoId],
    queryFn: () => api.listarMantenimientos(equipoId),
    enabled: !!equipoId,
    select: (pagina) => pagina.items,
  });
}

/** RNF-PERF-03 — listado general del laboratorio, paginado de verdad. */
export function useMantenimientos(pagina: number) {
  return useQuery({
    queryKey: [CLAVE, "todos", pagina],
    queryFn: () => api.listarMantenimientos(undefined, pagina),
    placeholderData: (anterior) => anterior,
  });
}

export function useMisMantenimientosDeHoy() {
  return useQuery({ queryKey: [CLAVE, "hoy"], queryFn: api.misMantenimientosDeHoy });
}

export function useEvidencias(mantenimientoId: string | undefined) {
  return useQuery({
    queryKey: [CLAVE, mantenimientoId, "evidencias"],
    queryFn: () => api.listarEvidencias(mantenimientoId as string),
    enabled: !!mantenimientoId,
  });
}

function useInvalidarMantenimientos(equipoId?: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: [CLAVE] });
    if (equipoId) queryClient.invalidateQueries({ queryKey: [CLAVE, "equipo", equipoId] });
    // Iniciar/cerrar un mantenimiento puede cambiar el estado operativo del
    // equipo (RN-MANT-01) y generar/resolver alertas (RF-ALT-01/RN-ALT-02).
    queryClient.invalidateQueries({ queryKey: ["equipos"] });
    queryClient.invalidateQueries({ queryKey: ["alertas"] });
  };
}

export function useCrearMantenimiento(equipoId: string) {
  const invalidar = useInvalidarMantenimientos(equipoId);
  return useMutation({
    mutationFn: (datos: DatosMantenimiento) => api.crearMantenimiento(datos),
    onSuccess: invalidar,
  });
}

export function useIniciarMantenimiento(equipoId?: string) {
  const invalidar = useInvalidarMantenimientos(equipoId);
  return useMutation({
    mutationFn: (id: string) => api.iniciarMantenimiento(id),
    onSuccess: invalidar,
  });
}

export function useCerrarMantenimiento(equipoId?: string) {
  const invalidar = useInvalidarMantenimientos(equipoId);
  return useMutation({
    mutationFn: ({ id, datos }: { id: string; datos: DatosCierre }) => api.cerrarMantenimiento(id, datos),
    onSuccess: invalidar,
  });
}

export function useCancelarMantenimiento(equipoId?: string) {
  const invalidar = useInvalidarMantenimientos(equipoId);
  return useMutation({
    mutationFn: ({ id, motivo }: { id: string; motivo: string }) => api.cancelarMantenimiento(id, motivo),
    onSuccess: invalidar,
  });
}

export function useAgregarEvidencia(mantenimientoId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (archivo: ArchivoConfirmado) => api.agregarEvidencia(mantenimientoId, archivo),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE, mantenimientoId, "evidencias"] }),
  });
}

export function useAsignarInforme(equipoId?: string) {
  const invalidar = useInvalidarMantenimientos(equipoId);
  return useMutation({
    mutationFn: ({ id, archivo }: { id: string; archivo: ArchivoConfirmado }) =>
      api.asignarInforme(id, archivo),
    onSuccess: invalidar,
  });
}
