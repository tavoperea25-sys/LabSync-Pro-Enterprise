import type { LucideIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { ApiError } from "@/lib/httpClient";

import { Button } from "./button";

const TAMANOS = {
  sm: { contenedor: "h-16 w-16", icono: "h-6 w-6" },
  md: { contenedor: "h-20 w-20", icono: "h-8 w-8" },
} as const;

export interface SubirFotoConPreviewProps {
  /** Texto encima del bloque — p. ej. "Fotografía" o "Logo". */
  etiqueta: string;
  /** URL ya persistida (viene del backend) — se muestra hasta que el
   * usuario suba un archivo nuevo. `null` mientras no haya ninguna. */
  urlActual: string | null;
  /** Sube el archivo al endpoint correspondiente (cada pantalla tiene el
   * suyo) y devuelve el `object_key` a persistir — el componente no sabe
   * nada de la API concreta, solo orquesta el estado de carga/preview/error
   * alrededor de esta función. */
  onSubir: (archivo: File) => Promise<string>;
  /** Se invoca con el nuevo `object_key` tras una subida exitosa, para que
   * la pantalla lo guarde y lo envíe al hacer submit del formulario. */
  onSubidoExitosamente: (objectKey: string) => void;
  /** Ícono mostrado cuando no hay ninguna foto/preview todavía. */
  iconoVacio: LucideIcon;
  /** Ícono del botón de subida (por defecto, el mismo que `iconoVacio`). */
  iconoBoton?: LucideIcon;
  textoBoton?: string;
  textoAyuda: string;
  altTexto: string;
  forma?: "circulo" | "cuadrado";
  tamano?: keyof typeof TAMANOS;
  accept?: string;
  mensajeErrorDefecto?: string;
}

/** Bloque reutilizable "subir foto con preview", usado por Equipos
 * (fotografía), Perfil (foto de usuario) y Configuración (logo
 * institucional) — antes triplicado casi al carácter en las 3 pantallas
 * (M8, Fase 2, docs/22-planificacion-fase2.md). Centraliza el ciclo de vida
 * del blob de preview: crea uno nuevo con `URL.createObjectURL` solo tras
 * una subida exitosa, revoca el anterior antes de reemplazarlo, y revoca el
 * vigente al desmontar — ninguna de las 3 pantallas originales revocaba
 * nunca, dejando un blob URL huérfano por cada foto subida en la sesión. */
export function SubirFotoConPreview({
  etiqueta,
  urlActual,
  onSubir,
  onSubidoExitosamente,
  iconoVacio: IconoVacio,
  iconoBoton,
  textoBoton = "Subir fotografía",
  textoAyuda,
  altTexto,
  forma = "cuadrado",
  tamano = "md",
  accept = "image/png,image/jpeg,image/webp",
  mensajeErrorDefecto = "No se pudo subir la fotografía.",
}: SubirFotoConPreviewProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  // Solo trackea el blob URL que este componente creó — nunca se revoca
  // `urlActual` (esa la resuelve el backend, no es un object URL nuestro).
  const blobUrlRef = useRef<string | null>(null);

  const [preview, setPreview] = useState<string | null>(urlActual);
  const [subiendo, setSubiendo] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // No pisa un preview local recién subido si `urlActual` cambia de
    // referencia por un re-render no relacionado (mismo criterio ya
    // aplicado en VistaMes/M10: sincronizar solo cuando corresponde).
    if (!blobUrlRef.current) {
      setPreview(urlActual);
    }
  }, [urlActual]);

  useEffect(() => {
    return () => {
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
      }
    };
  }, []);

  async function manejarSeleccion(archivo: File) {
    setError(null);
    setSubiendo(true);
    try {
      const objectKey = await onSubir(archivo);
      const nuevoBlobUrl = URL.createObjectURL(archivo);
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
      }
      blobUrlRef.current = nuevoBlobUrl;
      setPreview(nuevoBlobUrl);
      onSubidoExitosamente(objectKey);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : mensajeErrorDefecto);
    } finally {
      setSubiendo(false);
    }
  }

  const IconoDelBoton = iconoBoton ?? IconoVacio;
  const { contenedor, icono } = TAMANOS[tamano];

  return (
    <div className="mb-4">
      <p className="mb-1.5 text-sm font-semibold text-ink-soft">{etiqueta}</p>
      <div className="flex items-center gap-4">
        <div
          className={`flex ${contenedor} flex-shrink-0 items-center justify-center overflow-hidden border border-border bg-surface-alt ${
            forma === "circulo" ? "rounded-full" : "rounded-md"
          }`}
        >
          {preview ? (
            <img src={preview} alt={altTexto} className="h-full w-full object-cover" />
          ) : (
            <IconoVacio className={`${icono} text-ink-soft`} aria-hidden="true" />
          )}
        </div>
        <div>
          <input
            ref={inputRef}
            type="file"
            accept={accept}
            className="hidden"
            onChange={(e) => {
              const archivo = e.target.files?.[0];
              if (archivo) void manejarSeleccion(archivo);
            }}
          />
          <Button
            type="button"
            size="sm"
            variant="secondary"
            cargando={subiendo}
            onClick={() => inputRef.current?.click()}
          >
            <IconoDelBoton className="h-4 w-4" aria-hidden="true" />
            {textoBoton}
          </Button>
          <p className="mt-1.5 text-xs text-ink-soft">{textoAyuda}</p>
          {error && (
            <p role="alert" aria-live="polite" className="mt-1 text-xs font-medium text-danger">
              {error}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
