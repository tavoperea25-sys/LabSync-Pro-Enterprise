import { Layers, MapPin, Pencil, Plus, Trash2, X } from "lucide-react";
import { useState } from "react";

import { ApiError } from "@/lib/httpClient";
import { Button } from "@/shared/components/ui/button";
import { Checkbox } from "@/shared/components/ui/checkbox";
import { EmptyState } from "@/shared/components/ui/empty-state";
import { Input } from "@/shared/components/ui/input";
import { Skeleton } from "@/shared/components/ui/skeleton";

import {
  useActualizarArea,
  useActualizarCategoria,
  useAreas,
  useCategorias,
  useCrearArea,
  useCrearCategoria,
  useEliminarArea,
  useEliminarCategoria,
} from "../hooks/useConfiguracion";

export function CategoriasAreasSection() {
  return (
    <div className="grid max-w-4xl grid-cols-1 gap-8 lg:grid-cols-2">
      <CategoriasLista />
      <AreasLista />
    </div>
  );
}

function CategoriasLista() {
  const { data: categorias, isLoading } = useCategorias();
  const crear = useCrearCategoria();
  const actualizar = useActualizarCategoria();
  const eliminar = useEliminarCategoria();

  const [creando, setCreando] = useState(false);
  const [nombreNuevo, setNombreNuevo] = useState("");
  const [frecuenciaNueva, setFrecuenciaNueva] = useState("");
  const [bloqueaNueva, setBloqueaNueva] = useState(false);
  const [editandoId, setEditandoId] = useState<string | null>(null);
  const [nombreEdicion, setNombreEdicion] = useState("");
  const [frecuenciaEdicion, setFrecuenciaEdicion] = useState("");
  const [bloqueaEdicion, setBloqueaEdicion] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function confirmarCrear() {
    if (!nombreNuevo.trim()) return;
    setError(null);
    try {
      await crear.mutateAsync({
        nombre: nombreNuevo.trim(),
        frecuenciaMeses: frecuenciaNueva ? Number(frecuenciaNueva) : null,
        bloqueaActivacionSiCalibracionVencida: bloqueaNueva,
      });
      setNombreNuevo("");
      setFrecuenciaNueva("");
      setBloqueaNueva(false);
      setCreando(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear la categoría.");
    }
  }

  function iniciarEdicion(id: string, nombre: string, frecuencia: number | null, bloquea: boolean) {
    setEditandoId(id);
    setNombreEdicion(nombre);
    setFrecuenciaEdicion(frecuencia ? String(frecuencia) : "");
    setBloqueaEdicion(bloquea);
  }

  async function confirmarEdicion(id: string) {
    if (!nombreEdicion.trim()) return;
    setError(null);
    try {
      await actualizar.mutateAsync({
        id,
        nombre: nombreEdicion.trim(),
        frecuenciaMeses: frecuenciaEdicion ? Number(frecuenciaEdicion) : null,
        bloqueaActivacionSiCalibracionVencida: bloqueaEdicion,
      });
      setEditandoId(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar la categoría.");
    }
  }

  async function confirmarEliminar(id: string) {
    setError(null);
    try {
      await eliminar.mutateAsync(id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo eliminar la categoría.");
    }
  }

  return (
    <section>
      <h2 className="mb-1 flex items-center gap-2 font-display text-base font-semibold text-ink">
        <Layers className="h-4 w-4 text-primary-900" aria-hidden="true" />
        Categorías de equipo
      </h2>
      <p className="mb-4 text-sm text-ink-soft">
        Cada categoría puede tener una frecuencia de calibración por defecto (en meses).
      </p>

      {error && (
        <p role="alert" aria-live="polite" className="mb-3 text-sm font-medium text-danger">
          {error}
        </p>
      )}

      {isLoading && <Skeleton className="h-32 w-full" />}

      {!isLoading && categorias?.length === 0 && !creando && (
        <EmptyState icon={Layers} title="Sin categorías" description="Todavía no hay categorías de equipo." />
      )}

      {!!categorias?.length && (
        <ul className="mb-3 divide-y divide-border rounded-lg border border-border">
          {categorias.map((categoria) => (
            <li key={categoria.id} className="p-3">
              {editandoId === categoria.id ? (
                <div className="flex flex-wrap items-end gap-2">
                  <Input
                    label="Nombre"
                    value={nombreEdicion}
                    onChange={(e) => setNombreEdicion(e.target.value)}
                    className="mb-0"
                  />
                  <Input
                    label="Frecuencia (meses)"
                    type="number"
                    min={1}
                    value={frecuenciaEdicion}
                    onChange={(e) => setFrecuenciaEdicion(e.target.value)}
                    className="mb-0 w-36"
                  />
                  <div className="mb-4">
                    <Checkbox
                      name={`bloquea-edicion-${categoria.id}`}
                      label="Bloquea activar el equipo si su calibración está vencida"
                      checked={bloqueaEdicion}
                      onChange={(e) => setBloqueaEdicion(e.target.checked)}
                    />
                  </div>
                  <div className="mb-4 flex gap-1.5">
                    <Button size="sm" cargando={actualizar.isPending} onClick={() => confirmarEdicion(categoria.id)}>
                      Guardar
                    </Button>
                    <Button size="sm" variant="ghost" aria-label="Cancelar edición" onClick={() => setEditandoId(null)}>
                      <X className="h-4 w-4" aria-hidden="true" />
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <p className="text-sm font-medium text-ink">{categoria.nombre}</p>
                    <p className="text-xs text-ink-soft">
                      {categoria.frecuencia_calibracion_default_meses
                        ? `Calibración cada ${categoria.frecuencia_calibracion_default_meses} meses`
                        : "Sin frecuencia por defecto"}
                      {categoria.bloquea_activacion_si_calibracion_vencida &&
                        " · Bloquea activación si vencida"}
                    </p>
                  </div>
                  <div className="flex flex-shrink-0 gap-1">
                    <button
                      type="button"
                      aria-label={`Editar ${categoria.nombre}`}
                      className="rounded-sm p-1.5 text-ink-soft hover:bg-surface-alt hover:text-ink"
                      onClick={() =>
                        iniciarEdicion(
                          categoria.id,
                          categoria.nombre,
                          categoria.frecuencia_calibracion_default_meses,
                          categoria.bloquea_activacion_si_calibracion_vencida,
                        )
                      }
                    >
                      <Pencil className="h-4 w-4" aria-hidden="true" />
                    </button>
                    <button
                      type="button"
                      aria-label={`Eliminar ${categoria.nombre}`}
                      className="rounded-sm p-1.5 text-ink-soft hover:bg-surface-alt hover:text-danger"
                      onClick={() => confirmarEliminar(categoria.id)}
                    >
                      <Trash2 className="h-4 w-4" aria-hidden="true" />
                    </button>
                  </div>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      {creando ? (
        <div className="flex flex-wrap items-end gap-2 rounded-lg border border-border p-3">
          <Input
            label="Nombre"
            value={nombreNuevo}
            onChange={(e) => setNombreNuevo(e.target.value)}
            className="mb-0"
            autoFocus
          />
          <Input
            label="Frecuencia (meses)"
            type="number"
            min={1}
            value={frecuenciaNueva}
            onChange={(e) => setFrecuenciaNueva(e.target.value)}
            className="mb-0 w-36"
          />
          <div className="mb-4 w-full">
            <Checkbox
              name="bloquea-nueva"
              label="Bloquea activar el equipo si su calibración está vencida"
              checked={bloqueaNueva}
              onChange={(e) => setBloqueaNueva(e.target.checked)}
            />
          </div>
          <div className="mb-4 flex gap-1.5">
            <Button size="sm" cargando={crear.isPending} onClick={confirmarCrear}>
              Agregar
            </Button>
            <Button size="sm" variant="ghost" aria-label="Cancelar" onClick={() => setCreando(false)}>
              <X className="h-4 w-4" aria-hidden="true" />
            </Button>
          </div>
        </div>
      ) : (
        <Button size="sm" variant="secondary" onClick={() => setCreando(true)}>
          <Plus className="h-4 w-4" aria-hidden="true" />
          Nueva categoría
        </Button>
      )}
    </section>
  );
}

function AreasLista() {
  const { data: areas, isLoading } = useAreas();
  const crear = useCrearArea();
  const actualizar = useActualizarArea();
  const eliminar = useEliminarArea();

  const [creando, setCreando] = useState(false);
  const [nombreNuevo, setNombreNuevo] = useState("");
  const [editandoId, setEditandoId] = useState<string | null>(null);
  const [nombreEdicion, setNombreEdicion] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function confirmarCrear() {
    if (!nombreNuevo.trim()) return;
    setError(null);
    try {
      await crear.mutateAsync(nombreNuevo.trim());
      setNombreNuevo("");
      setCreando(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el área.");
    }
  }

  async function confirmarEdicion(id: string) {
    if (!nombreEdicion.trim()) return;
    setError(null);
    try {
      await actualizar.mutateAsync({ id, nombre: nombreEdicion.trim() });
      setEditandoId(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar el área.");
    }
  }

  async function confirmarEliminar(id: string) {
    setError(null);
    try {
      await eliminar.mutateAsync(id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo eliminar el área.");
    }
  }

  return (
    <section>
      <h2 className="mb-1 flex items-center gap-2 font-display text-base font-semibold text-ink">
        <MapPin className="h-4 w-4 text-primary-900" aria-hidden="true" />
        Áreas
      </h2>
      <p className="mb-4 text-sm text-ink-soft">Ubicaciones o secciones del laboratorio.</p>

      {error && (
        <p role="alert" aria-live="polite" className="mb-3 text-sm font-medium text-danger">
          {error}
        </p>
      )}

      {isLoading && <Skeleton className="h-32 w-full" />}

      {!isLoading && areas?.length === 0 && !creando && (
        <EmptyState icon={MapPin} title="Sin áreas" description="Todavía no hay áreas registradas." />
      )}

      {!!areas?.length && (
        <ul className="mb-3 divide-y divide-border rounded-lg border border-border">
          {areas.map((area) => (
            <li key={area.id} className="p-3">
              {editandoId === area.id ? (
                <div className="flex flex-wrap items-end gap-2">
                  <Input
                    label="Nombre"
                    value={nombreEdicion}
                    onChange={(e) => setNombreEdicion(e.target.value)}
                    className="mb-0"
                  />
                  <div className="mb-4 flex gap-1.5">
                    <Button size="sm" cargando={actualizar.isPending} onClick={() => confirmarEdicion(area.id)}>
                      Guardar
                    </Button>
                    <Button size="sm" variant="ghost" aria-label="Cancelar edición" onClick={() => setEditandoId(null)}>
                      <X className="h-4 w-4" aria-hidden="true" />
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium text-ink">{area.nombre}</p>
                  <div className="flex flex-shrink-0 gap-1">
                    <button
                      type="button"
                      aria-label={`Editar ${area.nombre}`}
                      className="rounded-sm p-1.5 text-ink-soft hover:bg-surface-alt hover:text-ink"
                      onClick={() => {
                        setEditandoId(area.id);
                        setNombreEdicion(area.nombre);
                      }}
                    >
                      <Pencil className="h-4 w-4" aria-hidden="true" />
                    </button>
                    <button
                      type="button"
                      aria-label={`Eliminar ${area.nombre}`}
                      className="rounded-sm p-1.5 text-ink-soft hover:bg-surface-alt hover:text-danger"
                      onClick={() => confirmarEliminar(area.id)}
                    >
                      <Trash2 className="h-4 w-4" aria-hidden="true" />
                    </button>
                  </div>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      {creando ? (
        <div className="flex flex-wrap items-end gap-2 rounded-lg border border-border p-3">
          <Input
            label="Nombre"
            value={nombreNuevo}
            onChange={(e) => setNombreNuevo(e.target.value)}
            className="mb-0"
            autoFocus
          />
          <div className="mb-4 flex gap-1.5">
            <Button size="sm" cargando={crear.isPending} onClick={confirmarCrear}>
              Agregar
            </Button>
            <Button size="sm" variant="ghost" aria-label="Cancelar" onClick={() => setCreando(false)}>
              <X className="h-4 w-4" aria-hidden="true" />
            </Button>
          </div>
        </div>
      ) : (
        <Button size="sm" variant="secondary" onClick={() => setCreando(true)}>
          <Plus className="h-4 w-4" aria-hidden="true" />
          Nueva área
        </Button>
      )}
    </section>
  );
}
