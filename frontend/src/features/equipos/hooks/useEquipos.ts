import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import * as api from "../api/equiposApi";
import type { EquipoRequest, FiltrosEquipos } from "../types";

const CLAVE_EQUIPOS = "equipos";

export function useEquipos(filtros: FiltrosEquipos) {
  return useQuery({
    queryKey: [CLAVE_EQUIPOS, filtros],
    queryFn: () => api.listarEquipos(filtros),
    placeholderData: (anterior) => anterior,
  });
}

export function useEquipo(id: string | undefined) {
  return useQuery({
    queryKey: [CLAVE_EQUIPOS, id],
    queryFn: () => api.obtenerEquipo(id as string),
    enabled: !!id,
  });
}

export function useCategorias() {
  return useQuery({ queryKey: ["categorias-equipo"], queryFn: api.listarCategorias });
}

export function useAreas() {
  return useQuery({ queryKey: ["areas"], queryFn: api.listarAreas });
}

export function useCrearEquipo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (datos: EquipoRequest) => api.crearEquipo(datos),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE_EQUIPOS] }),
  });
}

export function useActualizarEquipo(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (datos: EquipoRequest) => api.actualizarEquipo(id, datos),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE_EQUIPOS] }),
  });
}

export function useEliminarEquipo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.eliminarEquipo(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE_EQUIPOS] }),
  });
}

export function useDuplicarEquipo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.duplicarEquipo(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE_EQUIPOS] }),
  });
}

export function useHistorialEquipo(id: string | undefined) {
  return useQuery({
    queryKey: [CLAVE_EQUIPOS, id, "historial"],
    queryFn: () => api.obtenerHistorial(id as string),
    enabled: !!id,
  });
}

export function useQrInfo(id: string | undefined) {
  return useQuery({
    queryKey: [CLAVE_EQUIPOS, id, "qr"],
    queryFn: () => api.obtenerQrInfo(id as string),
    enabled: !!id,
  });
}

/** La imagen QR requiere el header Authorization (endpoint autenticado),
 * así que un <img src="..."> plano no sirve — se descarga como blob y se
 * expone como object URL, liberándola al desmontar o cambiar de equipo. */
export function useQrImagenUrl(id: string | undefined): string | null {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!id) {
      setUrl(null);
      return;
    }
    let cancelado = false;
    let objectUrl: string | null = null;

    api.obtenerImagenQrBlob(id).then((blob) => {
      if (cancelado) return;
      objectUrl = URL.createObjectURL(blob);
      setUrl(objectUrl);
    });

    return () => {
      cancelado = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [id]);

  return url;
}

export function useExportarEquipos() {
  return useMutation({
    mutationFn: async (filtros: FiltrosEquipos) => {
      const blob = await api.exportarEquiposBlob(filtros);
      const url = URL.createObjectURL(blob);
      const enlace = document.createElement("a");
      enlace.href = url;
      enlace.download = "equipos.xlsx";
      document.body.appendChild(enlace);
      enlace.click();
      enlace.remove();
      URL.revokeObjectURL(url);
    },
  });
}
