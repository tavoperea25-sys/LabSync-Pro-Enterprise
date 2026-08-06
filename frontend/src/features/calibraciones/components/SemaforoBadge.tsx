import { Badge } from "@/shared/components/ui/badge";

import { ETIQUETAS_SEMAFORO, type Semaforo } from "../types";

const VARIANTE_POR_SEMAFORO: Record<Semaforo, "success" | "warning" | "danger" | "neutral"> = {
  verde: "success",
  amarillo: "warning",
  rojo: "danger",
  gris: "neutral",
};

export function SemaforoBadge({ semaforo }: { semaforo: Semaforo }) {
  return <Badge variant={VARIANTE_POR_SEMAFORO[semaforo]}>{ETIQUETAS_SEMAFORO[semaforo]}</Badge>;
}
