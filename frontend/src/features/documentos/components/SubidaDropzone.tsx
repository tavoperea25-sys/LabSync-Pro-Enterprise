import { useQueryClient } from "@tanstack/react-query";
import { AlertCircle, CheckCircle2, Loader2, X } from "lucide-react";
import { useEffect, useRef } from "react";

import { crearDocumento, solicitarUrlSubida, subirArchivoConProgreso } from "../api/documentosApi";
import { formatearTamano } from "../types";

export interface ArchivoEnCola {
  id: string;
  archivo: File;
  progreso: number;
  estado: "pendiente" | "subiendo" | "listo" | "error";
  error?: string;
}

interface Props {
  cola: ArchivoEnCola[];
  setCola: React.Dispatch<React.SetStateAction<ArchivoEnCola[]>>;
  carpetaId: string | null;
  onSubidoTodo: () => void;
}

/** Panel flotante de progreso de subida. El drag & drop en sí vive en
 * `DocumentosPage` (DropzoneWrapper) — este componente solo procesa la cola
 * ya validada: pide la URL prefirmada, hace el PUT directo a MinIO con
 * progreso real (RF-DOC-01), y confirma el documento contra nuestro API. */
export function SubidaDropzone({ cola, setCola, carpetaId, onSubidoTodo }: Props) {
  const queryClient = useQueryClient();
  const enProceso = useRef<Set<string>>(new Set());

  useEffect(() => {
    const pendientes = cola.filter((item) => item.estado === "pendiente" && !enProceso.current.has(item.id));
    pendientes.forEach((item) => {
      enProceso.current.add(item.id);
      subir(item);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cola]);

  async function subir(item: ArchivoEnCola) {
    setCola((actual) => actual.map((a) => (a.id === item.id ? { ...a, estado: "subiendo" } : a)));
    try {
      const { url_subida, object_key } = await solicitarUrlSubida(
        item.archivo.name,
        item.archivo.type,
        item.archivo.size,
      );
      await subirArchivoConProgreso(url_subida, item.archivo, (progreso) => {
        setCola((actual) => actual.map((a) => (a.id === item.id ? { ...a, progreso } : a)));
      });
      const nombre = item.archivo.name.replace(/\.[^.]+$/, "") || item.archivo.name;
      await crearDocumento({
        nombre,
        carpeta_id: carpetaId,
        archivo: {
          object_key,
          nombre_archivo: item.archivo.name,
          tamano_bytes: item.archivo.size,
          tipo_mime: item.archivo.type,
        },
      });
      setCola((actual) => actual.map((a) => (a.id === item.id ? { ...a, estado: "listo", progreso: 100 } : a)));
      queryClient.invalidateQueries({ queryKey: ["documentos"] });
    } catch (error) {
      setCola((actual) =>
        actual.map((a) =>
          a.id === item.id ? { ...a, estado: "error", error: (error as Error).message } : a,
        ),
      );
    }
  }

  const todosTerminados = cola.every((item) => item.estado === "listo" || item.estado === "error");

  useEffect(() => {
    if (cola.length > 0 && todosTerminados) {
      const temporizador = setTimeout(onSubidoTodo, 1500);
      return () => clearTimeout(temporizador);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [todosTerminados, cola.length]);

  function quitar(id: string) {
    enProceso.current.delete(id);
    setCola((actual) => actual.filter((a) => a.id !== id));
  }

  if (cola.length === 0) return null;

  return (
    <div className="fixed bottom-6 right-6 z-40 w-80 rounded-lg border border-border bg-surface shadow-ambient">
      <div className="border-b border-border px-4 py-2.5 text-sm font-semibold text-ink">
        Subiendo {cola.length} archivo{cola.length !== 1 && "s"}
      </div>
      <ul className="max-h-72 space-y-1 overflow-y-auto p-2">
        {cola.map((item) => (
          <li key={item.id} className="flex items-start gap-2 rounded-md p-2 hover:bg-surface-alt">
            {item.estado === "listo" && (
              <CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-success" aria-hidden="true" />
            )}
            {item.estado === "error" && (
              <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-danger" aria-hidden="true" />
            )}
            {(item.estado === "subiendo" || item.estado === "pendiente") && (
              <Loader2 className="mt-0.5 h-4 w-4 flex-shrink-0 animate-spin text-primary-900" aria-hidden="true" />
            )}
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-medium text-ink">{item.archivo.name}</p>
              {item.estado === "error" ? (
                <p className="text-xs text-danger">{item.error}</p>
              ) : (
                <>
                  <p className="text-xs text-ink-soft">{formatearTamano(item.archivo.size)}</p>
                  {item.estado === "subiendo" && (
                    <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-surface-alt">
                      <div
                        className="h-full bg-primary-900 transition-all"
                        style={{ width: `${item.progreso}%` }}
                      />
                    </div>
                  )}
                </>
              )}
            </div>
            <button
              type="button"
              onClick={() => quitar(item.id)}
              aria-label="Quitar de la lista"
              className="text-ink-soft hover:text-ink"
            >
              <X className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
