import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as api from "../api/documentosApi";
import type { Carpeta, FiltrosDocumentos } from "../types";

const CLAVE_DOCUMENTOS = "documentos";
const CLAVE_CARPETAS = "carpetas";

export function useDocumentos(filtros: FiltrosDocumentos) {
  return useQuery({
    queryKey: [CLAVE_DOCUMENTOS, filtros],
    queryFn: () => api.listarDocumentos(filtros),
    placeholderData: (anterior) => anterior,
  });
}

export function useDocumentosRecientes() {
  return useQuery({ queryKey: [CLAVE_DOCUMENTOS, "recientes"], queryFn: api.listarRecientes });
}

export function usePapelera() {
  return useQuery({ queryKey: [CLAVE_DOCUMENTOS, "papelera"], queryFn: api.listarPapelera });
}

export function useDocumento(id: string | undefined) {
  return useQuery({
    queryKey: [CLAVE_DOCUMENTOS, id],
    queryFn: () => api.obtenerDocumento(id as string),
    enabled: !!id,
  });
}

export function useEtiquetas() {
  return useQuery({ queryKey: ["etiquetas"], queryFn: api.listarEtiquetas });
}

export function useCarpetas(carpetaPadreId: string | null | undefined) {
  return useQuery({
    queryKey: [CLAVE_CARPETAS, carpetaPadreId ?? "raiz"],
    queryFn: () => api.listarCarpetas(carpetaPadreId ?? undefined),
  });
}

export function useCarpeta(id: string | null | undefined) {
  return useQuery({
    queryKey: [CLAVE_CARPETAS, "detalle", id],
    queryFn: () => api.obtenerCarpeta(id as string),
    enabled: !!id,
  });
}

/** Reconstruye la ruta completa subiendo por `carpeta_padre_id` — así el
 * breadcrumb es correcto incluso entrando por un enlace directo a una
 * subcarpeta profunda, no solo navegando paso a paso desde la raíz. */
export function useMigasDePan(carpetaId: string | null) {
  return useQuery({
    queryKey: [CLAVE_CARPETAS, "migas", carpetaId],
    queryFn: async () => {
      const migas: Carpeta[] = [];
      let actualId: string | null = carpetaId;
      while (actualId) {
        const carpeta = await api.obtenerCarpeta(actualId);
        migas.unshift(carpeta);
        actualId = carpeta.carpeta_padre_id;
      }
      return migas;
    },
    enabled: !!carpetaId,
  });
}

function useInvalidarDocumentos() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: [CLAVE_DOCUMENTOS] });
}

export function useSubirNuevaVersion(documentoId: string) {
  const invalidar = useInvalidarDocumentos();
  return useMutation({
    mutationFn: (archivo: Parameters<typeof api.subirNuevaVersion>[1]) =>
      api.subirNuevaVersion(documentoId, archivo),
    onSuccess: invalidar,
  });
}

export function useActualizarMetadatos() {
  const invalidar = useInvalidarDocumentos();
  return useMutation({
    mutationFn: ({ id, datos }: { id: string; datos: Parameters<typeof api.actualizarMetadatos>[1] }) =>
      api.actualizarMetadatos(id, datos),
    onSuccess: invalidar,
  });
}

export function useAprobarDocumento() {
  const invalidar = useInvalidarDocumentos();
  return useMutation({
    mutationFn: (id: string) => api.aprobarDocumento(id),
    onSuccess: invalidar,
  });
}

export function useRechazarDocumento() {
  const invalidar = useInvalidarDocumentos();
  return useMutation({
    mutationFn: ({ id, comentario }: { id: string; comentario: string }) =>
      api.rechazarDocumento(id, comentario),
    onSuccess: invalidar,
  });
}

export function useRenombrarDocumento() {
  const invalidar = useInvalidarDocumentos();
  return useMutation({
    mutationFn: ({ id, nombre }: { id: string; nombre: string }) => api.renombrarDocumento(id, nombre),
    onSuccess: invalidar,
  });
}

export function useMoverDocumento() {
  const invalidar = useInvalidarDocumentos();
  return useMutation({
    mutationFn: ({ id, carpetaId }: { id: string; carpetaId: string | null }) =>
      api.moverDocumento(id, carpetaId),
    onSuccess: invalidar,
  });
}

export function useCopiarDocumento() {
  const invalidar = useInvalidarDocumentos();
  return useMutation({
    mutationFn: (id: string) => api.copiarDocumento(id),
    onSuccess: invalidar,
  });
}

export function useEliminarDocumento() {
  const invalidar = useInvalidarDocumentos();
  return useMutation({
    mutationFn: (id: string) => api.eliminarDocumento(id),
    onSuccess: invalidar,
  });
}

export function useRestaurarDocumento() {
  const invalidar = useInvalidarDocumentos();
  return useMutation({
    mutationFn: (id: string) => api.restaurarDocumento(id),
    onSuccess: invalidar,
  });
}

export function useAlternarFavorito() {
  const invalidar = useInvalidarDocumentos();
  return useMutation({
    mutationFn: (id: string) => api.alternarFavorito(id),
    onSuccess: invalidar,
  });
}

export function useAsignarEtiqueta(documentoId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (nombre: string) => api.asignarEtiqueta(documentoId, nombre),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [CLAVE_DOCUMENTOS, documentoId] });
      queryClient.invalidateQueries({ queryKey: ["etiquetas"] });
    },
  });
}

export function useQuitarEtiqueta(documentoId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (etiquetaId: string) => api.quitarEtiqueta(documentoId, etiquetaId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE_DOCUMENTOS, documentoId] }),
  });
}

export function useCrearCarpeta() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ nombre, carpetaPadreId }: { nombre: string; carpetaPadreId: string | null }) =>
      api.crearCarpeta(nombre, carpetaPadreId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE_CARPETAS] }),
  });
}

export function useRenombrarCarpeta() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, nombre }: { id: string; nombre: string }) => api.renombrarCarpeta(id, nombre),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE_CARPETAS] }),
  });
}

export function useEliminarCarpeta() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.eliminarCarpeta(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE_CARPETAS] }),
  });
}
