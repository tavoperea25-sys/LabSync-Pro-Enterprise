import { useMutation, useQuery } from "@tanstack/react-query";

import * as api from "../api/auditoriaApi";
import type { FiltrosAuditoria, FormatoExportacion } from "../types";

export function useAuditoria(filtros: FiltrosAuditoria) {
  return useQuery({
    queryKey: ["auditoria", filtros],
    queryFn: () => api.listarAuditoria(filtros),
    placeholderData: (anterior) => anterior,
  });
}

export function useValoresFiltro() {
  return useQuery({ queryKey: ["auditoria", "valores-filtro"], queryFn: api.obtenerValoresFiltro });
}

const NOMBRE_ARCHIVO: Record<FormatoExportacion, string> = {
  csv: "auditoria.csv",
  xlsx: "auditoria.xlsx",
  pdf: "auditoria.pdf",
};

export function useExportarAuditoria() {
  return useMutation({
    mutationFn: async ({ formato, filtros }: { formato: FormatoExportacion; filtros: FiltrosAuditoria }) => {
      const blob = await api.exportarAuditoria(formato, filtros);
      const url = URL.createObjectURL(blob);
      const enlace = document.createElement("a");
      enlace.href = url;
      enlace.download = NOMBRE_ARCHIVO[formato];
      document.body.appendChild(enlace);
      enlace.click();
      enlace.remove();
      URL.revokeObjectURL(url);
    },
  });
}
