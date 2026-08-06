import { useMutation, useQuery } from "@tanstack/react-query";

import * as api from "../api/qrApi";
import type { IncidenciaRequest } from "../types";

export function useEquipoPorQr(token: string | undefined) {
  return useQuery({
    queryKey: ["qr", token],
    queryFn: () => api.obtenerEquipoPorQr(token as string),
    enabled: !!token,
    retry: false,
  });
}

export function useReportarIncidencia(token: string) {
  return useMutation({
    mutationFn: (datos: IncidenciaRequest) => api.reportarIncidencia(token, datos),
  });
}
