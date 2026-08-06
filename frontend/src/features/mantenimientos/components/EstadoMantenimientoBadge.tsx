import { Badge } from "@/shared/components/ui/badge";

import { ETIQUETAS_ESTADO_MANTENIMIENTO, type EstadoMantenimiento } from "../types";

const VARIANTE_POR_ESTADO: Record<EstadoMantenimiento, "success" | "warning" | "danger" | "neutral"> = {
  programado: "neutral",
  en_ejecucion: "warning",
  completado: "success",
  cancelado: "danger",
};

export function EstadoMantenimientoBadge({ estado }: { estado: EstadoMantenimiento }) {
  return <Badge variant={VARIANTE_POR_ESTADO[estado]}>{ETIQUETAS_ESTADO_MANTENIMIENTO[estado]}</Badge>;
}
