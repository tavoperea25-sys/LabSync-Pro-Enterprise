import { apiFetch } from "@/lib/httpClient";

import type { ResultadoBusqueda } from "../types";

export async function buscar(q: string): Promise<ResultadoBusqueda[]> {
  return apiFetch<ResultadoBusqueda[]>(`/busqueda?q=${encodeURIComponent(q)}`);
}
