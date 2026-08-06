import { useQuery } from "@tanstack/react-query";

import * as api from "../api/busquedaApi";

export function useBusqueda(consulta: string) {
  return useQuery({
    queryKey: ["busqueda", consulta],
    queryFn: () => api.buscar(consulta),
    enabled: consulta.trim().length >= 2,
  });
}
