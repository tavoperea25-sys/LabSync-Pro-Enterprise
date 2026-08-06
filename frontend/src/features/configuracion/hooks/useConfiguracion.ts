import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as api from "../api/configuracionApi";
import type {
  ActualizarUmbrales,
  DatosCambiarPassword,
  DatosPerfilPropio,
  MapeoEstadosMantenimiento,
  PoliticaPassword,
} from "../types";

const CLAVE = "configuracion";

export function useConfiguracion() {
  return useQuery({ queryKey: [CLAVE], queryFn: api.obtenerConfiguracion });
}

export function useActualizarUmbrales() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (datos: ActualizarUmbrales) => api.actualizarUmbrales(datos),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE] }),
  });
}

export function useActualizarPoliticaPassword() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (politica: PoliticaPassword | null) => api.actualizarPoliticaPassword(politica),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE] }),
  });
}

export function useActualizarMapeoEstadosMantenimiento() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (mapeo: MapeoEstadosMantenimiento | null) => api.actualizarMapeoEstadosMantenimiento(mapeo),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE] }),
  });
}

export function useInstitucion() {
  return useQuery({ queryKey: [CLAVE, "institucion"], queryFn: api.obtenerInstitucion });
}

export function useActualizarInstitucion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ nombre, logoObjectKey }: { nombre: string; logoObjectKey: string | null }) =>
      api.actualizarInstitucion(nombre, logoObjectKey),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE, "institucion"] }),
  });
}

export function useCategorias() {
  return useQuery({ queryKey: [CLAVE, "categorias"], queryFn: api.listarCategorias });
}

export function useCrearCategoria() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      nombre,
      frecuenciaMeses,
      bloqueaActivacionSiCalibracionVencida,
    }: {
      nombre: string;
      frecuenciaMeses: number | null;
      bloqueaActivacionSiCalibracionVencida: boolean;
    }) => api.crearCategoria(nombre, frecuenciaMeses, bloqueaActivacionSiCalibracionVencida),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE, "categorias"] }),
  });
}

export function useActualizarCategoria() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      nombre,
      frecuenciaMeses,
      bloqueaActivacionSiCalibracionVencida,
    }: {
      id: string;
      nombre: string;
      frecuenciaMeses: number | null;
      bloqueaActivacionSiCalibracionVencida: boolean;
    }) => api.actualizarCategoria(id, nombre, frecuenciaMeses, bloqueaActivacionSiCalibracionVencida),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE, "categorias"] }),
  });
}

export function useEliminarCategoria() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.eliminarCategoria(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE, "categorias"] }),
  });
}

export function useAreas() {
  return useQuery({ queryKey: [CLAVE, "areas"], queryFn: api.listarAreas });
}

export function useCrearArea() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (nombre: string) => api.crearArea(nombre),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE, "areas"] }),
  });
}

export function useActualizarArea() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, nombre }: { id: string; nombre: string }) => api.actualizarArea(id, nombre),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE, "areas"] }),
  });
}

export function useEliminarArea() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.eliminarArea(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE, "areas"] }),
  });
}

export function useActualizarPerfilPropio() {
  return useMutation({
    mutationFn: (datos: DatosPerfilPropio) => api.actualizarPerfilPropio(datos),
  });
}

export function useCambiarPasswordPropio() {
  return useMutation({
    mutationFn: (datos: DatosCambiarPassword) => api.cambiarPasswordPropio(datos),
  });
}

export function useExportarDatosTenant() {
  return useMutation({
    mutationFn: async () => {
      const blob = await api.exportarDatosTenant();
      const url = URL.createObjectURL(blob);
      const enlace = document.createElement("a");
      enlace.href = url;
      enlace.download = "labsync-exportacion-datos.zip";
      document.body.appendChild(enlace);
      enlace.click();
      enlace.remove();
      URL.revokeObjectURL(url);
    },
  });
}
