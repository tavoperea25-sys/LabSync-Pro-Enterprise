import { Search } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useDebouncedValue } from "@/shared/hooks/useDebouncedValue";

import { useBusqueda } from "../hooks/useBusqueda";
import { ETIQUETAS_TIPO_RESULTADO, type ResultadoBusqueda, type TipoResultado } from "../types";

const ORDEN_TIPOS: TipoResultado[] = [
  "equipo",
  "documento",
  "calibracion",
  "mantenimiento",
  "usuario",
  "auditoria",
];

function agruparPorTipo(resultados: ResultadoBusqueda[]): [TipoResultado, ResultadoBusqueda[]][] {
  const grupos = new Map<TipoResultado, ResultadoBusqueda[]>();
  for (const r of resultados) grupos.set(r.tipo, [...(grupos.get(r.tipo) ?? []), r]);
  return ORDEN_TIPOS.filter((t) => grupos.has(t)).map((t) => [t, grupos.get(t) as ResultadoBusqueda[]]);
}

const SELECTOR_FOCUSABLE = 'input, button:not([tabindex="-1"]), [href], [tabindex]:not([tabindex="-1"])';

/** RF-SEARCH-01 a 04 — omnibox global, Cmd/Ctrl+K desde cualquier pantalla,
 * resultados agrupados por tipo de entidad, navegable completamente por
 * teclado. Reemplaza el stub visual de búsqueda en `Navbar.tsx`. */
export function Omnibox() {
  const navigate = useNavigate();
  const [abierto, setAbierto] = useState(false);
  const [consulta, setConsulta] = useState("");
  const [indiceActivo, setIndiceActivo] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const botonAbrirRef = useRef<HTMLButtonElement>(null);
  const dialogoRef = useRef<HTMLDivElement>(null);
  const consultaDebounced = useDebouncedValue(consulta, 250);

  const { data: resultados, isFetching } = useBusqueda(consultaDebounced);
  const grupos = useMemo(() => agruparPorTipo(resultados ?? []), [resultados]);
  const lista = resultados ?? [];

  useEffect(() => {
    function alPresionar(evt: KeyboardEvent) {
      if ((evt.metaKey || evt.ctrlKey) && evt.key.toLowerCase() === "k") {
        evt.preventDefault();
        setAbierto(true);
      } else if (evt.key === "Escape" && abierto) {
        setAbierto(false);
      }
    }
    document.addEventListener("keydown", alPresionar);
    return () => document.removeEventListener("keydown", alPresionar);
  }, [abierto]);

  useEffect(() => {
    if (!abierto) return;
    setConsulta("");
    setIndiceActivo(0);
    // Espera al siguiente frame para que el input ya esté montado.
    requestAnimationFrame(() => inputRef.current?.focus());
    // Se copia la referencia al botón disparador vigente en este momento —
    // el botón nunca se desmonta mientras la app corre, pero copiar evita
    // depender de esa garantía (mismo consejo que da el propio lint de
    // react-hooks para refs leídas en la limpieza de un efecto).
    const botonDisparador = botonAbrirRef.current;
    // La función de limpieza de ESTA instancia del efecto (la que corrió
    // porque `abierto` era true) se dispara cuando `abierto` pasa a false
    // — sin importar qué haya disparado el cierre: Escape, clic en el
    // fondo, o seleccionar un resultado y navegar. Un solo lugar para
    // devolver el foco, en vez de repetirlo en cada callback que puede
    // cerrar el diálogo.
    return () => {
      botonDisparador?.focus();
    };
  }, [abierto]);

  useEffect(() => {
    setIndiceActivo(0);
  }, [resultados]);

  function irAResultado(resultado: ResultadoBusqueda) {
    setAbierto(false);
    navigate(resultado.ruta);
  }

  function alPresionarEnInput(evt: React.KeyboardEvent<HTMLInputElement>) {
    if (evt.key === "ArrowDown") {
      evt.preventDefault();
      setIndiceActivo((i) => Math.min(i + 1, lista.length - 1));
    } else if (evt.key === "ArrowUp") {
      evt.preventDefault();
      setIndiceActivo((i) => Math.max(i - 1, 0));
    } else if (evt.key === "Enter" && lista[indiceActivo]) {
      evt.preventDefault();
      irAResultado(lista[indiceActivo]);
    }
  }

  /** Trampa de foco manual (sin librería externa, mismo criterio que el
   * resto del proyecto — ver el cierre por clic-afuera de
   * `NotificacionesBell.tsx`): con `aria-modal="true"` el foco no debe
   * poder escapar del diálogo con Tab/Shift+Tab. Se consultan los elementos
   * focoseables en cada pulsación (no se cachean) porque la lista de
   * resultados cambia mientras el diálogo está abierto. */
  function alPresionarTeclaEnDialogo(evt: React.KeyboardEvent<HTMLDivElement>) {
    if (evt.key !== "Tab" || !dialogoRef.current) return;
    const focosables = Array.from(
      dialogoRef.current.querySelectorAll<HTMLElement>(SELECTOR_FOCUSABLE),
    );
    if (focosables.length === 0) return;
    const primero = focosables[0];
    const ultimo = focosables[focosables.length - 1];
    if (!primero || !ultimo) return;
    if (evt.shiftKey && document.activeElement === primero) {
      evt.preventDefault();
      ultimo.focus();
    } else if (!evt.shiftKey && document.activeElement === ultimo) {
      evt.preventDefault();
      primero.focus();
    }
  }

  return (
    <>
      <button
        ref={botonAbrirRef}
        type="button"
        onClick={() => setAbierto(true)}
        className="flex h-10 w-full max-w-sm items-center gap-2 rounded-md border border-border px-3 text-sm text-ink-soft transition-colors duration-fast hover:border-primary-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-900"
        aria-label="Buscar"
        aria-haspopup="dialog"
        aria-expanded={abierto}
        aria-controls="omnibox-dialogo"
      >
        <Search className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
        <span className="truncate">Buscar equipos, documentos…</span>
        <kbd className="ml-auto hidden rounded border border-border bg-surface-alt px-1.5 py-0.5 text-[10px] font-medium text-ink-soft sm:inline">
          ⌘K
        </kbd>
      </button>

      {abierto && (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 p-4 pt-[15vh]">
          <button
            type="button"
            tabIndex={-1}
            aria-label="Cerrar búsqueda"
            className="absolute inset-0 cursor-default"
            onClick={() => setAbierto(false)}
          />
          <div
            id="omnibox-dialogo"
            ref={dialogoRef}
            role="dialog"
            aria-modal="true"
            aria-label="Búsqueda global"
            onKeyDown={alPresionarTeclaEnDialogo}
            className="relative z-10 w-full max-w-xl overflow-hidden rounded-lg border border-border bg-surface shadow-ambient"
          >
            <div className="flex items-center gap-2 border-b border-border px-4">
              <Search className="h-4 w-4 flex-shrink-0 text-ink-soft" aria-hidden="true" />
              <input
                ref={inputRef}
                type="text"
                role="combobox"
                aria-label="Buscar"
                aria-expanded={lista.length > 0}
                aria-controls="omnibox-resultados"
                value={consulta}
                onChange={(e) => setConsulta(e.target.value)}
                onKeyDown={alPresionarEnInput}
                placeholder="Buscar equipos, documentos, certificados, usuarios…"
                className="h-12 w-full bg-transparent text-sm text-ink outline-none placeholder:text-ink-soft focus-visible:ring-2 focus-visible:ring-primary-900/40 focus-visible:ring-offset-0"
              />
              <kbd className="rounded border border-border bg-surface-alt px-1.5 py-0.5 text-[10px] font-medium text-ink-soft">
                Esc
              </kbd>
            </div>

            <div id="omnibox-resultados" className="max-h-96 overflow-y-auto p-2">
              {consulta.trim().length > 0 && consulta.trim().length < 2 && (
                <p className="px-2 py-6 text-center text-sm text-ink-soft">Escribe al menos 2 caracteres…</p>
              )}
              {isFetching && <p className="px-2 py-6 text-center text-sm text-ink-soft">Buscando…</p>}
              {!isFetching && consultaDebounced.trim().length >= 2 && lista.length === 0 && (
                <p className="px-2 py-6 text-center text-sm text-ink-soft">Sin resultados.</p>
              )}
              {!isFetching &&
                grupos.map(([tipo, resultadosDelTipo]) => (
                  <div key={tipo} className="mb-2">
                    <p className="px-2 py-1 text-xs font-semibold uppercase tracking-wide text-ink-soft">
                      {ETIQUETAS_TIPO_RESULTADO[tipo]}
                    </p>
                    {resultadosDelTipo.map((resultado) => {
                      const indiceGlobal = lista.indexOf(resultado);
                      return (
                        <button
                          key={`${resultado.tipo}-${resultado.id}`}
                          type="button"
                          onMouseEnter={() => setIndiceActivo(indiceGlobal)}
                          onClick={() => irAResultado(resultado)}
                          className={`flex w-full flex-col items-start rounded-md px-2 py-1.5 text-left ${
                            indiceGlobal === indiceActivo ? "bg-primary-tint" : "hover:bg-surface-alt"
                          }`}
                        >
                          <span className="truncate text-sm font-medium text-ink">{resultado.titulo}</span>
                          {resultado.subtitulo && (
                            <span className="truncate text-xs text-ink-soft">{resultado.subtitulo}</span>
                          )}
                        </button>
                      );
                    })}
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
