import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  Check,
  CheckCircle2,
  Copy,
  Download,
  File,
  Folder,
  Home,
  Loader2,
  Pencil,
  Plus,
  Star,
  Tag,
  Trash2,
  Upload,
  X,
  XCircle,
} from "lucide-react";
import { useRef, useState } from "react";
import { useNavigate, useParams } from "react-router";

import { ApiError } from "@/lib/httpClient";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";

import * as api from "../api/documentosApi";
import {
  useActualizarMetadatos,
  useAlternarFavorito,
  useAprobarDocumento,
  useAsignarEtiqueta,
  useCarpetas,
  useCopiarDocumento,
  useDocumento,
  useEliminarDocumento,
  useMoverDocumento,
  useQuitarEtiqueta,
  useRechazarDocumento,
  useRenombrarDocumento,
  useSubirNuevaVersion,
} from "../hooks/useDocumentos";
import { formatearTamano, formatoPermitido, TAMANO_MAXIMO_BYTES, type DocumentoDetalle } from "../types";
import { DocumentoEstadoBadge } from "./DocumentoEstadoBadge";

function useVistaPrevia(documentoId: string | undefined) {
  return useQuery({
    queryKey: ["documentos", documentoId, "vista-previa"],
    queryFn: () => api.obtenerVistaPrevia(documentoId as string),
    enabled: !!documentoId,
  });
}

export function DocumentoDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: documento, isLoading } = useDocumento(id);
  const { data: vistaPrevia } = useVistaPrevia(id);
  const renombrar = useRenombrarDocumento();
  const mover = useMoverDocumento();
  const copiar = useCopiarDocumento();
  const eliminar = useEliminarDocumento();
  const alternarFavorito = useAlternarFavorito();
  const asignarEtiqueta = useAsignarEtiqueta(id ?? "");
  const quitarEtiqueta = useQuitarEtiqueta(id ?? "");
  const subirNuevaVersion = useSubirNuevaVersion(id ?? "");
  const aprobar = useAprobarDocumento();
  const rechazar = useRechazarDocumento();
  const actualizarMetadatos = useActualizarMetadatos();

  const [editandoNombre, setEditandoNombre] = useState(false);
  const [nombreEditado, setNombreEditado] = useState("");
  const [nuevaEtiqueta, setNuevaEtiqueta] = useState("");
  const [mostrandoMover, setMostrandoMover] = useState(false);
  const [confirmandoEliminar, setConfirmandoEliminar] = useState(false);
  const [subiendoVersion, setSubiendoVersion] = useState(false);
  const [errorVersion, setErrorVersion] = useState<string | null>(null);
  const [rechazando, setRechazando] = useState(false);
  const [comentarioRechazo, setComentarioRechazo] = useState("");
  const [editandoMetadatos, setEditandoMetadatos] = useState(false);
  const [errorAprobacion, setErrorAprobacion] = useState<string | null>(null);
  const inputVersionRef = useRef<HTMLInputElement>(null);

  if (isLoading) return <div className="p-8 text-sm text-ink-soft">Cargando documento…</div>;
  if (!documento) return <div className="p-8 text-sm text-ink-soft">Este documento no existe o fue eliminado.</div>;

  async function confirmarRenombrar() {
    if (!id || !nombreEditado.trim()) {
      setEditandoNombre(false);
      return;
    }
    await renombrar.mutateAsync({ id, nombre: nombreEditado.trim() });
    setEditandoNombre(false);
  }

  async function confirmarCopiar() {
    if (!id) return;
    const copia = await copiar.mutateAsync(id);
    navigate(`/documentos/${copia.id}`);
  }

  async function confirmarEliminar() {
    if (!id) return;
    await eliminar.mutateAsync(id);
    navigate("/documentos");
  }

  async function confirmarAprobar() {
    if (!id) return;
    setErrorAprobacion(null);
    try {
      await aprobar.mutateAsync(id);
    } catch (error) {
      setErrorAprobacion(error instanceof ApiError ? error.message : "No se pudo aprobar el documento.");
    }
  }

  async function confirmarRechazar() {
    if (!id || !comentarioRechazo.trim()) return;
    setErrorAprobacion(null);
    try {
      await rechazar.mutateAsync({ id, comentario: comentarioRechazo.trim() });
      setComentarioRechazo("");
      setRechazando(false);
    } catch (error) {
      setErrorAprobacion(error instanceof ApiError ? error.message : "No se pudo rechazar el documento.");
    }
  }

  async function agregarEtiqueta() {
    if (!nuevaEtiqueta.trim()) return;
    await asignarEtiqueta.mutateAsync(nuevaEtiqueta.trim());
    setNuevaEtiqueta("");
  }

  async function descargarVersion(numero: number) {
    if (!id) return;
    const { url } = await api.obtenerUrlDescarga(id, numero);
    window.open(url, "_blank", "noopener,noreferrer");
  }

  async function subirVersion(archivo: File) {
    if (!id) return;
    setErrorVersion(null);
    if (!formatoPermitido(archivo.name, archivo.type)) {
      setErrorVersion("Formato no permitido.");
      return;
    }
    if (archivo.size > TAMANO_MAXIMO_BYTES) {
      setErrorVersion("El archivo supera 50 MB.");
      return;
    }
    setSubiendoVersion(true);
    try {
      const { url_subida, object_key } = await api.solicitarUrlSubida(archivo.name, archivo.type, archivo.size);
      await api.subirArchivoConProgreso(url_subida, archivo, () => {});
      await subirNuevaVersion.mutateAsync({
        object_key,
        nombre_archivo: archivo.name,
        tamano_bytes: archivo.size,
        tipo_mime: archivo.type,
      });
    } catch (error) {
      setErrorVersion(error instanceof ApiError ? error.message : "No se pudo subir la nueva versión.");
    } finally {
      setSubiendoVersion(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl p-6 sm:p-8">
      <button
        type="button"
        onClick={() => navigate("/documentos")}
        className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-ink-soft hover:text-ink"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Volver a Documentos
      </button>

      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          {editandoNombre ? (
            <div className="flex items-center gap-2">
              <input
                autoFocus
                aria-label="Nombre del documento"
                value={nombreEditado}
                onChange={(e) => setNombreEditado(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && confirmarRenombrar()}
                className="h-10 w-full max-w-md rounded-sm border border-border bg-surface px-3 text-lg font-semibold text-ink outline-none focus:border-primary-900 focus:ring-4 focus:ring-primary-900/15"
              />
              <Button size="sm" cargando={renombrar.isPending} onClick={confirmarRenombrar}>
                <Check className="h-4 w-4" aria-hidden="true" />
              </Button>
              <Button variant="secondary" size="sm" aria-label="Cancelar renombrar" onClick={() => setEditandoNombre(false)}>
                <X className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <h1 className="font-display truncate text-2xl font-semibold text-ink">{documento.nombre}</h1>
              <button
                type="button"
                title="Renombrar"
                aria-label="Renombrar documento"
                onClick={() => {
                  setNombreEditado(documento.nombre);
                  setEditandoNombre(true);
                }}
                className="flex-shrink-0 rounded p-1 text-ink-soft hover:text-ink"
              >
                <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            </div>
          )}
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <DocumentoEstadoBadge estado={documento.estado_efectivo} />
            {documento.categoria && <Badge variant="neutral">{documento.categoria}</Badge>}
          </div>
        </div>

        <div className="flex flex-shrink-0 flex-wrap gap-2">
          {documento.estado === "en_revision" && (
            <>
              <Button variant="secondary" size="sm" cargando={aprobar.isPending} onClick={confirmarAprobar}>
                <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                Aprobar
              </Button>
              <Button variant="destructive" size="sm" onClick={() => setRechazando(true)}>
                <XCircle className="h-4 w-4" aria-hidden="true" />
                Rechazar
              </Button>
            </>
          )}
          <Button
            variant="secondary"
            size="sm"
            title="Alternar favorito"
            aria-label={documento.es_favorito ? "Quitar de favoritos" : "Marcar como favorito"}
            onClick={() => id && alternarFavorito.mutate(id)}
          >
            <Star
              className={documento.es_favorito ? "h-4 w-4 fill-warning text-warning" : "h-4 w-4"}
              aria-hidden="true"
            />
          </Button>
          <Button variant="secondary" size="sm" cargando={copiar.isPending} onClick={confirmarCopiar}>
            <Copy className="h-4 w-4" aria-hidden="true" />
            Copiar
          </Button>
          <Button variant="destructive" size="sm" onClick={() => setConfirmandoEliminar(true)}>
            <Trash2 className="h-4 w-4" aria-hidden="true" />
            Eliminar
          </Button>
        </div>
      </div>

      {errorAprobacion && (
        <p role="alert" aria-live="polite" className="mb-4 text-sm font-medium text-danger">
          {errorAprobacion}
        </p>
      )}

      {rechazando && (
        <div className="mb-6 rounded-md border border-danger/30 bg-[#FEF2F2] p-4">
          <p className="mb-2 text-sm font-semibold text-[#991B1B]">Motivo del rechazo</p>
          <textarea
            autoFocus
            value={comentarioRechazo}
            onChange={(e) => setComentarioRechazo(e.target.value)}
            placeholder="Explica qué debe corregirse antes de volver a subirlo…"
            rows={3}
            className="mb-3 w-full rounded-sm border border-border bg-surface px-3 py-2 text-sm text-ink outline-none focus:border-danger focus:ring-4 focus:ring-danger/15"
          />
          <div className="flex gap-2">
            <Button
              variant="destructive"
              size="sm"
              cargando={rechazar.isPending}
              disabled={!comentarioRechazo.trim()}
              onClick={confirmarRechazar}
            >
              Confirmar rechazo
            </Button>
            <Button variant="secondary" size="sm" onClick={() => setRechazando(false)}>
              Cancelar
            </Button>
          </div>
        </div>
      )}

      {documento.estado === "en_revision" && documento.ultimo_rechazo && (
        <div className="mb-6 flex items-start gap-2 rounded-md border border-danger/30 bg-[#FEF2F2] p-4">
          <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-danger" aria-hidden="true" />
          <div>
            <p className="text-sm font-semibold text-[#991B1B]">
              Rechazado el {new Date(documento.ultimo_rechazo.creado_en).toLocaleString("es-CO")}
            </p>
            <p className="text-sm text-[#7F1D1D]">{documento.ultimo_rechazo.comentario}</p>
          </div>
        </div>
      )}

      {confirmandoEliminar && (
        <div role="alertdialog" className="mb-6 rounded-md border border-danger/30 bg-[#FEF2F2] p-4">
          <p className="mb-1 text-sm font-semibold text-[#991B1B]">¿Enviar este documento a la papelera?</p>
          <p className="mb-3 text-sm text-[#7F1D1D]">
            Podrás restaurarlo desde la papelera mientras no se purgue definitivamente.
          </p>
          <div className="flex gap-2">
            <Button variant="destructive" size="sm" cargando={eliminar.isPending} onClick={confirmarEliminar}>
              Sí, eliminar
            </Button>
            <Button variant="secondary" size="sm" onClick={() => setConfirmandoEliminar(false)}>
              Cancelar
            </Button>
          </div>
        </div>
      )}

      {/* Previsualización — RF-DOC-07 */}
      <div className="mb-4 overflow-hidden rounded-lg border border-border bg-surface">
        {vistaPrevia?.url ? (
          vistaPrevia.tipo_mime.startsWith("image/") ? (
            <img src={vistaPrevia.url} alt={`Previsualización de ${vistaPrevia.nombre_archivo}`} className="max-h-[480px] w-full object-contain" />
          ) : (
            <iframe title={`Previsualización de ${vistaPrevia.nombre_archivo}`} src={vistaPrevia.url} className="h-[480px] w-full" />
          )
        ) : (
          <div className="flex flex-col items-center gap-2 p-10 text-center">
            <File className="h-10 w-10 text-ink-soft" aria-hidden="true" />
            <p className="text-sm text-ink-soft">
              {vistaPrevia
                ? `Sin previsualización disponible para .${vistaPrevia.nombre_archivo.split(".").pop()} — usa Descargar.`
                : "Cargando…"}
            </p>
          </div>
        )}
      </div>

      {/* Ubicación — mover */}
      <div className="mb-4 rounded-lg border border-border p-4">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-soft">Ubicación</h2>
          <Button variant="secondary" size="sm" onClick={() => setMostrandoMover((v) => !v)}>
            <Folder className="h-4 w-4" aria-hidden="true" />
            Mover
          </Button>
        </div>
        {mostrandoMover && id && (
          <SelectorDeCarpeta
            onMover={async (carpetaId) => {
              await mover.mutateAsync({ id, carpetaId });
              setMostrandoMover(false);
            }}
            moviendo={mover.isPending}
          />
        )}
      </div>

      {/* Metadatos de vigencia — RF-DOC-12 */}
      <div className="mb-4 rounded-lg border border-border p-4">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-soft">
            Categoría y vigencia
          </h2>
          {!editandoMetadatos && (
            <Button variant="secondary" size="sm" onClick={() => setEditandoMetadatos(true)}>
              <Pencil className="h-4 w-4" aria-hidden="true" />
              Editar
            </Button>
          )}
        </div>
        {editandoMetadatos ? (
          <FormularioMetadatos
            documento={documento}
            guardando={actualizarMetadatos.isPending}
            onCancelar={() => setEditandoMetadatos(false)}
            onGuardar={async (datos) => {
              if (!id) return;
              await actualizarMetadatos.mutateAsync({ id, datos });
              setEditandoMetadatos(false);
            }}
          />
        ) : (
          <dl className="grid grid-cols-1 gap-x-4 gap-y-3 sm:grid-cols-3">
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-ink-soft">Categoría</dt>
              <dd className="mt-0.5 text-sm text-ink">{documento.categoria || "—"}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-ink-soft">Fecha de emisión</dt>
              <dd className="mt-0.5 text-sm text-ink">{documento.fecha_emision || "—"}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-ink-soft">
                Fecha de vencimiento
              </dt>
              <dd className="mt-0.5 text-sm text-ink">{documento.fecha_vencimiento || "—"}</dd>
            </div>
          </dl>
        )}
      </div>

      {/* Etiquetas — RF-DOC-04 */}
      <div className="mb-4 rounded-lg border border-border p-4">
        <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-soft">Etiquetas</h2>
        <div className="mb-3 flex flex-wrap gap-2">
          {documento.etiquetas.length === 0 && <p className="text-sm text-ink-soft">Sin etiquetas todavía.</p>}
          {documento.etiquetas.map((etiqueta) => (
            <span
              key={etiqueta.id}
              className="inline-flex items-center gap-1 rounded-full bg-surface-alt px-2.5 py-1 text-xs font-medium text-ink"
            >
              <Tag className="h-3 w-3" aria-hidden="true" />
              {etiqueta.nombre}
              <button
                type="button"
                aria-label={`Quitar etiqueta ${etiqueta.nombre}`}
                onClick={() => id && quitarEtiqueta.mutate(etiqueta.id)}
                className="ml-0.5 text-ink-soft hover:text-ink"
              >
                <X className="h-3 w-3" aria-hidden="true" />
              </button>
            </span>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            value={nuevaEtiqueta}
            onChange={(e) => setNuevaEtiqueta(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && agregarEtiqueta()}
            placeholder="Nueva etiqueta…"
            aria-label="Nueva etiqueta"
            className="h-9 flex-1 rounded-sm border border-border bg-surface px-3 text-sm text-ink outline-none focus:border-primary-900 focus:ring-4 focus:ring-primary-900/15"
          />
          <Button size="sm" cargando={asignarEtiqueta.isPending} onClick={agregarEtiqueta}>
            <Plus className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>
      </div>

      {/* Versiones — RF-DOC-11 */}
      <div className="rounded-lg border border-border p-4">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-soft">Historial de versiones</h2>
          <Button
            variant="secondary"
            size="sm"
            cargando={subiendoVersion}
            onClick={() => inputVersionRef.current?.click()}
          >
            <Upload className="h-4 w-4" aria-hidden="true" />
            Nueva versión
          </Button>
          <input
            ref={inputVersionRef}
            type="file"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && subirVersion(e.target.files[0])}
          />
        </div>
        {errorVersion && (
          <p role="alert" aria-live="polite" className="mb-3 text-xs font-medium text-danger">
            {errorVersion}
          </p>
        )}
        <ul className="space-y-2">
          {documento.versiones.map((version) => (
            <li key={version.id} className="flex items-center justify-between gap-2 rounded-md border border-border p-3">
              <div className="min-w-0">
                <p className="text-sm font-medium text-ink">
                  v{version.numero_version} — {version.nombre_archivo}
                </p>
                <p className="text-xs text-ink-soft">
                  {formatearTamano(version.tamano_bytes)} · {new Date(version.creado_en).toLocaleString("es-CO")}
                </p>
                <p className="text-xs text-ink-soft">
                  {version.aprobado_en
                    ? `Aprobada el ${new Date(version.aprobado_en).toLocaleString("es-CO")}`
                    : "Pendiente de aprobación"}
                </p>
              </div>
              <Button variant="secondary" size="sm" onClick={() => descargarVersion(version.numero_version)}>
                <Download className="h-4 w-4" aria-hidden="true" />
              </Button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function FormularioMetadatos({
  documento,
  guardando,
  onGuardar,
  onCancelar,
}: {
  documento: DocumentoDetalle;
  guardando: boolean;
  onGuardar: (datos: {
    categoria: string | null;
    fecha_emision: string | null;
    fecha_vencimiento: string | null;
  }) => void;
  onCancelar: () => void;
}) {
  const [categoria, setCategoria] = useState(documento.categoria ?? "");
  const [fechaEmision, setFechaEmision] = useState(documento.fecha_emision ?? "");
  const [fechaVencimiento, setFechaVencimiento] = useState(documento.fecha_vencimiento ?? "");

  return (
    <div>
      <div className="grid grid-cols-1 gap-x-4 gap-y-3 sm:grid-cols-3">
        <div>
          <label className="mb-1 block text-xs font-semibold text-ink-soft" htmlFor="categoria-doc">
            Categoría
          </label>
          <input
            id="categoria-doc"
            value={categoria}
            onChange={(e) => setCategoria(e.target.value)}
            className="h-9 w-full rounded-sm border border-border bg-surface px-3 text-sm text-ink outline-none focus:border-primary-900 focus:ring-4 focus:ring-primary-900/15"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-semibold text-ink-soft" htmlFor="fecha-emision-doc">
            Fecha de emisión
          </label>
          <input
            id="fecha-emision-doc"
            type="date"
            value={fechaEmision}
            onChange={(e) => setFechaEmision(e.target.value)}
            className="h-9 w-full rounded-sm border border-border bg-surface px-3 text-sm text-ink outline-none focus:border-primary-900 focus:ring-4 focus:ring-primary-900/15"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-semibold text-ink-soft" htmlFor="fecha-vencimiento-doc">
            Fecha de vencimiento
          </label>
          <input
            id="fecha-vencimiento-doc"
            type="date"
            value={fechaVencimiento}
            onChange={(e) => setFechaVencimiento(e.target.value)}
            className="h-9 w-full rounded-sm border border-border bg-surface px-3 text-sm text-ink outline-none focus:border-primary-900 focus:ring-4 focus:ring-primary-900/15"
          />
        </div>
      </div>
      <div className="mt-3 flex gap-2">
        <Button
          size="sm"
          cargando={guardando}
          onClick={() =>
            onGuardar({
              categoria: categoria.trim() || null,
              fecha_emision: fechaEmision || null,
              fecha_vencimiento: fechaVencimiento || null,
            })
          }
        >
          Guardar
        </Button>
        <Button variant="secondary" size="sm" onClick={onCancelar}>
          Cancelar
        </Button>
      </div>
    </div>
  );
}

function SelectorDeCarpeta({
  onMover,
  moviendo,
}: {
  onMover: (carpetaId: string | null) => void;
  moviendo: boolean;
}) {
  const [carpetaId, setCarpetaId] = useState<string | null>(null);
  const { data: subcarpetas, isLoading } = useCarpetas(carpetaId);

  return (
    <div className="rounded-md border border-border bg-surface-alt p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={() => setCarpetaId(null)}
          className="inline-flex items-center gap-1 text-sm font-medium text-ink-soft hover:text-ink"
        >
          <Home className="h-3.5 w-3.5" aria-hidden="true" />
          Raíz
        </button>
        <Button size="sm" cargando={moviendo} onClick={() => onMover(carpetaId)}>
          Mover aquí
        </Button>
      </div>
      {isLoading && <p className="text-xs text-ink-soft">Cargando…</p>}
      {!isLoading && !subcarpetas?.length && <p className="text-xs text-ink-soft">Sin subcarpetas.</p>}
      {!!subcarpetas?.length && (
        <ul className="space-y-1">
          {subcarpetas.map((carpeta) => (
            <li key={carpeta.id}>
              <button
                type="button"
                onClick={() => setCarpetaId(carpeta.id)}
                className="inline-flex w-full items-center gap-1.5 rounded px-2 py-1 text-left text-sm text-ink hover:bg-surface"
              >
                <Folder className="h-3.5 w-3.5 text-primary-900" aria-hidden="true" />
                {carpeta.nombre}
              </button>
            </li>
          ))}
        </ul>
      )}
      {moviendo && <Loader2 className="mt-2 h-4 w-4 animate-spin text-primary-900" aria-hidden="true" />}
    </div>
  );
}
