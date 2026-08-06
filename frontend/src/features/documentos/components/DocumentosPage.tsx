import {
  AlertTriangle,
  Check,
  ChevronRight,
  File,
  FilePlus2,
  Folder,
  FolderPlus,
  Home,
  Search,
  Star,
  Trash2,
  UploadCloud,
  X,
} from "lucide-react";
import { useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { ApiError } from "@/lib/httpClient";
import { Button } from "@/shared/components/ui/button";
import { EmptyState } from "@/shared/components/ui/empty-state";
import { LinkButton } from "@/shared/components/ui/link-button";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { useDebouncedValue } from "@/shared/hooks/useDebouncedValue";

import {
  useAlternarFavorito,
  useCarpetas,
  useCrearCarpeta,
  useDocumentos,
  useMigasDePan,
} from "../hooks/useDocumentos";
import { formatoPermitido, TAMANO_MAXIMO_BYTES } from "../types";
import { DocumentoEstadoBadge } from "./DocumentoEstadoBadge";
import { SubidaDropzone, type ArchivoEnCola } from "./SubidaDropzone";

export function DocumentosPage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const carpetaId = params.get("carpeta");
  const [busqueda, setBusqueda] = useState("");
  const [soloFavoritos, setSoloFavoritos] = useState(false);
  const [creandoCarpeta, setCreandoCarpeta] = useState(false);
  const [nombreCarpeta, setNombreCarpeta] = useState("");
  const [errorCarpeta, setErrorCarpeta] = useState<string | null>(null);
  const [cola, setCola] = useState<ArchivoEnCola[]>([]);
  const inputArchivoRef = useRef<HTMLInputElement>(null);

  const qDebounced = useDebouncedValue(busqueda);
  const { data: migas } = useMigasDePan(carpetaId);
  const { data: subcarpetas, isLoading: cargandoCarpetas } = useCarpetas(carpetaId);
  const { data: pagina, isLoading: cargandoDocs, isError: errorDocs } = useDocumentos({
    carpeta_id: carpetaId ?? undefined,
    q: qDebounced || undefined,
    favoritos: soloFavoritos,
  });
  const crearCarpeta = useCrearCarpeta();
  const alternarFavorito = useAlternarFavorito();

  function navegarACarpeta(id: string | null) {
    if (id) setParams({ carpeta: id });
    else setParams({});
  }

  async function confirmarNuevaCarpeta() {
    if (!nombreCarpeta.trim()) {
      setCreandoCarpeta(false);
      return;
    }
    setErrorCarpeta(null);
    try {
      await crearCarpeta.mutateAsync({ nombre: nombreCarpeta.trim(), carpetaPadreId: carpetaId });
      setNombreCarpeta("");
      setCreandoCarpeta(false);
    } catch (error) {
      setErrorCarpeta(error instanceof ApiError ? error.message : "No se pudo crear la carpeta.");
    }
  }

  function encolarArchivos(archivos: FileList | File[]) {
    const nuevos: ArchivoEnCola[] = Array.from(archivos).map((archivo) => {
      let error: string | undefined;
      if (!formatoPermitido(archivo.name, archivo.type)) error = "Formato no permitido.";
      else if (archivo.size > TAMANO_MAXIMO_BYTES) error = "El archivo supera 50 MB.";
      return { id: crypto.randomUUID(), archivo, progreso: 0, estado: error ? "error" : "pendiente", error };
    });
    setCola((actual) => [...actual, ...nuevos]);
  }

  const mostrarBusquedaOFavoritos = !!qDebounced || soloFavoritos;

  return (
    <div className="p-6 sm:p-8">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <nav aria-label="Ruta de carpetas" className="flex flex-wrap items-center gap-1 text-sm">
          <button
            type="button"
            onClick={() => navegarACarpeta(null)}
            className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 font-medium text-ink-soft hover:bg-surface-alt hover:text-ink"
          >
            <Home className="h-4 w-4" aria-hidden="true" />
            Documentos
          </button>
          {migas?.map((miga) => (
            <span key={miga.id} className="flex items-center gap-1">
              <ChevronRight className="h-3.5 w-3.5 text-ink-soft" aria-hidden="true" />
              <button
                type="button"
                onClick={() => navegarACarpeta(miga.id)}
                className="rounded px-1.5 py-0.5 font-medium text-ink-soft hover:bg-surface-alt hover:text-ink"
              >
                {miga.nombre}
              </button>
            </span>
          ))}
        </nav>

        <div className="flex flex-wrap gap-2">
          <LinkButton to="/documentos/papelera" variant="secondary" size="sm">
            <Trash2 className="h-4 w-4" aria-hidden="true" />
            Papelera
          </LinkButton>
          <Button variant="secondary" size="sm" onClick={() => setCreandoCarpeta(true)}>
            <FolderPlus className="h-4 w-4" aria-hidden="true" />
            Carpeta
          </Button>
          <Button size="sm" onClick={() => inputArchivoRef.current?.click()}>
            <FilePlus2 className="h-4 w-4" aria-hidden="true" />
            Subir
          </Button>
          <input
            ref={inputArchivoRef}
            type="file"
            multiple
            className="hidden"
            onChange={(e) => e.target.files && encolarArchivos(e.target.files)}
          />
        </div>
      </div>

      <div className="mb-5 flex flex-wrap gap-2.5">
        <div className="relative min-w-[220px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-soft" aria-hidden="true" />
          <input
            type="search"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            placeholder="Buscar documentos…"
            aria-label="Buscar documentos"
            className="h-10 w-full rounded-md border border-border bg-surface pl-9 pr-3 text-sm text-ink outline-none transition-colors duration-fast placeholder:text-ink-soft focus:border-primary-900 focus:ring-4 focus:ring-primary-900/15"
          />
        </div>
        <Button
          variant={soloFavoritos ? "primary" : "secondary"}
          size="sm"
          onClick={() => setSoloFavoritos((v) => !v)}
        >
          <Star className="h-4 w-4" aria-hidden="true" />
          Favoritos
        </Button>
      </div>

      {creandoCarpeta && (
        <div className="mb-4 rounded-md border border-border bg-surface p-3">
          <div className="flex items-center gap-2">
            <Folder className="h-4 w-4 text-primary-900" aria-hidden="true" />
            <input
              autoFocus
              value={nombreCarpeta}
              onChange={(e) => {
                setNombreCarpeta(e.target.value);
                setErrorCarpeta(null);
              }}
              onKeyDown={(e) => e.key === "Enter" && confirmarNuevaCarpeta()}
              placeholder="Nombre de la carpeta"
              aria-label="Nombre de la nueva carpeta"
              aria-invalid={!!errorCarpeta}
              className="h-9 flex-1 rounded-sm border border-border bg-surface px-3 text-sm text-ink outline-none focus:border-primary-900 focus:ring-4 focus:ring-primary-900/15"
            />
            <Button
              size="sm"
              aria-label="Crear carpeta"
              cargando={crearCarpeta.isPending}
              onClick={confirmarNuevaCarpeta}
            >
              <Check className="h-4 w-4" aria-hidden="true" />
            </Button>
            <Button
              variant="secondary"
              size="sm"
              aria-label="Cancelar nueva carpeta"
              onClick={() => {
                setCreandoCarpeta(false);
                setErrorCarpeta(null);
              }}
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </Button>
          </div>
          {errorCarpeta && (
            <p role="alert" aria-live="polite" className="mt-1.5 pl-6 text-xs font-medium text-danger">
              {errorCarpeta}
            </p>
          )}
        </div>
      )}

      <DropzoneWrapper onArchivos={encolarArchivos}>
        {!mostrarBusquedaOFavoritos && (
          <>
            {cargandoCarpetas && (
              <div className="mb-4 grid grid-cols-2 gap-2.5 sm:grid-cols-3 md:grid-cols-4">
                {Array.from({ length: 3 }).map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            )}
            {!!subcarpetas?.length && (
              <div className="mb-5 grid grid-cols-2 gap-2.5 sm:grid-cols-3 md:grid-cols-4">
                {subcarpetas.map((carpeta) => (
                  <button
                    key={carpeta.id}
                    type="button"
                    onClick={() => navegarACarpeta(carpeta.id)}
                    className="flex items-center gap-2.5 rounded-lg border border-border bg-surface p-3.5 text-left transition-colors duration-fast hover:bg-surface-alt"
                  >
                    <Folder className="h-5 w-5 flex-shrink-0 text-primary-900" aria-hidden="true" />
                    <span className="truncate text-sm font-medium text-ink">{carpeta.nombre}</span>
                  </button>
                ))}
              </div>
            )}
          </>
        )}

        {cargandoDocs && (
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-14 w-full" />
            ))}
          </div>
        )}

        {errorDocs && (
          <EmptyState
            icon={AlertTriangle}
            title="No se pudo cargar el listado"
            description="Intenta de nuevo en unos segundos."
          />
        )}

        {!cargandoDocs && !errorDocs && pagina && pagina.items.length === 0 && !subcarpetas?.length && (
          <EmptyState
            icon={File}
            title="Esta carpeta está vacía"
            description="Arrastra archivos aquí o usa el botón «Subir» para empezar."
          />
        )}

        {!cargandoDocs && !errorDocs && !!pagina?.items.length && (
          <ul className="divide-y divide-border overflow-hidden rounded-lg border border-border">
            {pagina.items.map((documento) => (
              <li key={documento.id} className="flex items-center gap-3 bg-surface px-4 py-3 hover:bg-surface-alt">
                <button
                  type="button"
                  onClick={() => navigate(`/documentos/${documento.id}`)}
                  className="flex min-w-0 flex-1 items-center gap-3 text-left"
                >
                  <File className="h-5 w-5 flex-shrink-0 text-ink-soft" aria-hidden="true" />
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-medium text-ink">{documento.nombre}</span>
                    {documento.categoria && (
                      <span className="block truncate text-xs text-ink-soft">{documento.categoria}</span>
                    )}
                  </span>
                </button>
                <DocumentoEstadoBadge estado={documento.estado_efectivo} />
                <button
                  type="button"
                  title="Alternar favorito"
                  aria-label="Alternar favorito"
                  onClick={() => alternarFavorito.mutate(documento.id)}
                  className="flex-shrink-0 rounded p-1 text-ink-soft hover:text-warning"
                >
                  <Star className="h-4 w-4" aria-hidden="true" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </DropzoneWrapper>

      {cola.length > 0 && (
        <SubidaDropzone
          cola={cola}
          setCola={setCola}
          carpetaId={carpetaId}
          onSubidoTodo={() => setCola((actual) => actual.filter((a) => a.estado === "error"))}
        />
      )}
    </div>
  );
}

function DropzoneWrapper({
  children,
  onArchivos,
}: {
  children: React.ReactNode;
  onArchivos: (archivos: FileList) => void;
}) {
  const [arrastrando, setArrastrando] = useState(false);
  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setArrastrando(true);
      }}
      onDragLeave={() => setArrastrando(false)}
      onDrop={(e) => {
        e.preventDefault();
        setArrastrando(false);
        if (e.dataTransfer.files.length) onArchivos(e.dataTransfer.files);
      }}
      className={
        arrastrando
          ? "rounded-lg outline-dashed outline-2 outline-offset-4 outline-primary-900"
          : undefined
      }
    >
      {arrastrando && (
        <div className="mb-4 flex items-center gap-2 rounded-md bg-primary-tint p-3 text-sm font-medium text-primary-900">
          <UploadCloud className="h-4 w-4" aria-hidden="true" />
          Suelta los archivos para subirlos aquí
        </div>
      )}
      {children}
    </div>
  );
}
