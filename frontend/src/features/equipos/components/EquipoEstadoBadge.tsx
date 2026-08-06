import { Badge } from "@/shared/components/ui/badge";

import { ETIQUETAS_ESTADO, type EstadoOperativo } from "../types";

const VARIANTE_POR_ESTADO: Record<EstadoOperativo, "success" | "warning" | "danger" | "neutral"> = {
  operativo: "success",
  en_mantenimiento: "warning",
  fuera_de_servicio: "danger",
  de_baja: "neutral",
};

export function EquipoEstadoBadge({ estado }: { estado: EstadoOperativo }) {
  return <Badge variant={VARIANTE_POR_ESTADO[estado]}>{ETIQUETAS_ESTADO[estado]}</Badge>;
}
