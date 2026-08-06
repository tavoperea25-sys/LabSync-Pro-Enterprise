import { Badge } from "@/shared/components/ui/badge";

import { ETIQUETAS_TIPO_ALERTA, type TipoAlerta } from "../types";

const VARIANTE_POR_TIPO: Record<TipoAlerta, "danger" | "warning"> = {
  critica: "danger",
  preventiva: "warning",
};

export function AlertaTipoBadge({ tipo }: { tipo: TipoAlerta }) {
  return <Badge variant={VARIANTE_POR_TIPO[tipo]}>{ETIQUETAS_TIPO_ALERTA[tipo]}</Badge>;
}
