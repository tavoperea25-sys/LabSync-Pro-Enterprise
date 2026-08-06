import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as api from "../api/usuariosApi";
import type { DatosActualizarUsuario, DatosCrearUsuario } from "../types";

const CLAVE = "usuarios";

export function useRoles() {
  return useQuery({ queryKey: ["roles"], queryFn: api.listarRoles });
}

export function useUsuarios(pagina = 1, tamanoPagina?: number) {
  return useQuery({
    queryKey: [CLAVE, pagina, tamanoPagina],
    queryFn: () => api.listarUsuarios(pagina, tamanoPagina),
    placeholderData: (anterior) => anterior,
  });
}

export function useSesiones(usuarioId: string | undefined) {
  return useQuery({
    queryKey: [CLAVE, usuarioId, "sesiones"],
    queryFn: () => api.listarSesiones(usuarioId as string),
    enabled: !!usuarioId,
  });
}

export function useCrearUsuario() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (datos: DatosCrearUsuario) => api.crearUsuario(datos),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE] }),
  });
}

export function useActualizarUsuario() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, datos }: { id: string; datos: DatosActualizarUsuario }) =>
      api.actualizarUsuario(id, datos),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE] }),
  });
}

export function useActivarUsuario() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.activarUsuario(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE] }),
  });
}

export function useDesactivarUsuario() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.desactivarUsuario(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE] }),
  });
}

export function useAsignarRoles() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, rolIds }: { id: string; rolIds: string[] }) => api.asignarRoles(id, rolIds),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE] }),
  });
}

export function useCerrarSesion(usuarioId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sesionId: string) => api.cerrarSesion(usuarioId, sesionId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE, usuarioId, "sesiones"] }),
  });
}
