import { Badge } from "@/shared/components/ui/badge";

const VARIANTE_POR_ESTADO: Record<string, "success" | "warning" | "neutral"> = {
  activo: "success",
  inactivo: "neutral",
  pendiente_activacion: "warning",
};

const ETIQUETAS: Record<string, string> = {
  activo: "Activo",
  inactivo: "Inactivo",
  pendiente_activacion: "Pendiente de activación",
};

export function EstadoUsuarioBadge({ estado }: { estado: string }) {
  return <Badge variant={VARIANTE_POR_ESTADO[estado] ?? "neutral"}>{ETIQUETAS[estado] ?? estado}</Badge>;
}
