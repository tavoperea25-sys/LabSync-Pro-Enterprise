import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as api from "../api/calibracionesApi";
import type { DatosCalibracion } from "../types";

const CLAVE = "calibraciones";

export function useCalibracionesPorEquipo(equipoId: string | undefined) {
  return useQuery({
    queryKey: [CLAVE, "equipo", equipoId],
    queryFn: () => api.listarPorEquipo(equipoId as string),
    enabled: !!equipoId,
  });
}

export function useCriticos() {
  return useQuery({ queryKey: [CLAVE, "criticas"], queryFn: api.listarCriticos });
}

export function useCrearCalibracion(equipoId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (datos: DatosCalibracion) => api.crearCalibracion(datos),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [CLAVE, "equipo", equipoId] });
      queryClient.invalidateQueries({ queryKey: [CLAVE, "criticas"] });
    },
  });
}

export function useCorregirCalibracion(equipoId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, datos }: { id: string; datos: DatosCalibracion & { motivo: string } }) =>
      api.corregirCalibracion(id, datos),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [CLAVE, "equipo", equipoId] });
      queryClient.invalidateQueries({ queryKey: [CLAVE, "criticas"] });
    },
  });
}
