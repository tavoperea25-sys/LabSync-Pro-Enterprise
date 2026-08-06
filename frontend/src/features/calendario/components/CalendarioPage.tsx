import { ChevronLeft, ChevronRight, Plus } from "lucide-react";
import { useMemo, useState } from "react";

import { useAreas } from "@/features/equipos/hooks/useEquipos";
import { Button } from "@/shared/components/ui/button";
import { Select } from "@/shared/components/ui/select";
import { Skeleton } from "@/shared/components/ui/skeleton";

import {
  useCrearEvento,
  useActualizarEvento,
  useEliminarEvento,
  useEventos,
} from "../hooks/useCalendario";
import {
  ETIQUETAS_TIPO_EVENTO,
  TIPOS_EVENTO_MANUAL,
  type DatosEventoCalendario,
  type EventoCalendario,
  type TipoEvento,
  type VistaCalendario,
} from "../types";
import { avanzar, calcularRango } from "./CalendarioPage.logic";
import { EventoFormulario } from "./EventoFormulario";
import { VistaAgenda } from "./VistaAgenda";
import { VistaMes } from "./VistaMes";

const TODOS_LOS_TIPOS: TipoEvento[] = [
  ...TIPOS_EVENTO_MANUAL,
  "calibracion",
  "mantenimiento",
  "vencimiento_documental",
];

const ETIQUETAS_VISTA: Record<VistaCalendario, string> = {
  dia: "Día",
  semana: "Semana",
  mes: "Mes",
  agenda: "Agenda",
};

export function CalendarioPage() {
  const [vista, setVista] = useState<VistaCalendario>("mes");
  const [fechaRef, setFechaRef] = useState(() => new Date());
  const [tipoFiltro, setTipoFiltro] = useState<TipoEvento | "">("");
  const [areaFiltro, setAreaFiltro] = useState("");
  const [formulario, setFormulario] = useState<{ editando?: EventoCalendario; fechaInicial?: string } | null>(
    null,
  );

  const { data: areas } = useAreas();
  const rango = useMemo(() => calcularRango(vista, fechaRef), [vista, fechaRef]);
  const { data: eventos, isLoading } = useEventos({
    desde: rango.desde.toISOString(),
    hasta: rango.hasta.toISOString(),
    tipo: tipoFiltro || undefined,
    areaId: areaFiltro || undefined,
  });

  const crear = useCrearEvento();
  const actualizar = useActualizarEvento();
  const eliminar = useEliminarEvento();

  async function guardar(datos: DatosEventoCalendario) {
    if (formulario?.editando) {
      await actualizar.mutateAsync({ id: formulario.editando.id, datos });
    } else {
      await crear.mutateAsync(datos);
    }
    setFormulario(null);
  }

  async function eliminarEditando() {
    if (!formulario?.editando) return;
    await eliminar.mutateAsync(formulario.editando.id);
    setFormulario(null);
  }

  const tituloRango =
    vista === "mes"
      ? fechaRef.toLocaleDateString("es-CO", { month: "long", year: "numeric" })
      : vista === "agenda"
        ? "Próximos 90 días"
        : `${rango.desde.toLocaleDateString("es-CO", { day: "numeric", month: "short" })} – ${rango.hasta.toLocaleDateString("es-CO", { day: "numeric", month: "short" })}`;

  return (
    <div className="p-6 sm:p-8">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="mb-1 font-display text-2xl font-semibold text-ink">Calendario</h1>
          <p className="text-sm text-ink-soft">
            Calibraciones, mantenimientos, vencimientos documentales y eventos institucionales.
          </p>
        </div>
        <Button
          size="sm"
          onClick={() => setFormulario({ fechaInicial: new Date().toISOString() })}
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          Nuevo evento
        </Button>
      </div>

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            aria-label="Período anterior"
            onClick={() => setFechaRef(avanzar(vista, fechaRef, -1))}
          >
            <ChevronLeft className="h-4 w-4" aria-hidden="true" />
          </Button>
          <span className="min-w-40 text-center text-sm font-semibold capitalize text-ink">{tituloRango}</span>
          <Button
            variant="secondary"
            size="sm"
            aria-label="Período siguiente"
            onClick={() => setFechaRef(avanzar(vista, fechaRef, 1))}
          >
            <ChevronRight className="h-4 w-4" aria-hidden="true" />
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setFechaRef(new Date())}>
            Hoy
          </Button>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex rounded-md border border-border p-0.5">
            {(Object.keys(ETIQUETAS_VISTA) as VistaCalendario[]).map((v) => (
              <button
                key={v}
                type="button"
                onClick={() => setVista(v)}
                className={`rounded px-3 py-1.5 text-sm font-medium transition-colors ${
                  vista === v ? "bg-primary-900 text-white" : "text-ink-soft hover:bg-surface-alt"
                }`}
              >
                {ETIQUETAS_VISTA[v]}
              </button>
            ))}
          </div>
          <div className="w-44">
            <Select
              label="Tipo"
              value={tipoFiltro}
              onChange={(e) => setTipoFiltro(e.target.value as TipoEvento | "")}
            >
              <option value="">Todos los tipos</option>
              {TODOS_LOS_TIPOS.map((t) => (
                <option key={t} value={t}>
                  {ETIQUETAS_TIPO_EVENTO[t]}
                </option>
              ))}
            </Select>
          </div>
          {!!areas?.length && (
            <div className="w-40">
              <Select label="Área" value={areaFiltro} onChange={(e) => setAreaFiltro(e.target.value)}>
                <option value="">Toda área</option>
                {areas.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.nombre}
                  </option>
                ))}
              </Select>
            </div>
          )}
        </div>
      </div>

      {formulario && (
        <div className="mb-4">
          <EventoFormulario
            editando={formulario.editando}
            fechaInicial={formulario.fechaInicial}
            guardando={crear.isPending || actualizar.isPending}
            onGuardar={guardar}
            onCancelar={() => setFormulario(null)}
          />
          {formulario.editando && (
            <Button
              variant="destructive"
              size="sm"
              cargando={eliminar.isPending}
              onClick={eliminarEditando}
              className="mt-2"
            >
              Eliminar evento
            </Button>
          )}
        </div>
      )}

      {isLoading && <Skeleton className="h-96 w-full" />}

      {!isLoading && eventos && vista === "mes" && (
        <VistaMes
          fechaDeReferencia={fechaRef}
          eventos={eventos}
          onEditar={(evento) => setFormulario({ editando: evento })}
          onCrearEnFecha={(fecha) => setFormulario({ fechaInicial: fecha.toISOString() })}
        />
      )}

      {!isLoading && eventos && vista !== "mes" && (
        <VistaAgenda eventos={eventos} onEditar={(evento) => setFormulario({ editando: evento })} />
      )}
    </div>
  );
}
