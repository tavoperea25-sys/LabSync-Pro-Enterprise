import { useEffect, useState } from "react";

/** RNF-PERF / docs/11-design-system.md: eventos de alta frecuencia (input
 * de búsqueda) se debouncean antes de disparar la petición. */
export function useDebouncedValue<T>(valor: T, retrasoMs = 300): T {
  const [valorDebounced, setValorDebounced] = useState(valor);

  useEffect(() => {
    const timeout = setTimeout(() => setValorDebounced(valor), retrasoMs);
    return () => clearTimeout(timeout);
  }, [valor, retrasoMs]);

  return valorDebounced;
}
