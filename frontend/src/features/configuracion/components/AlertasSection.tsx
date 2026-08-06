import { Bell, ShieldCheck, Wrench } from "lucide-react";
import { useEffect, useState } from "react";

import { ETIQUETAS_TIPO, TIPOS_MANTENIMIENTO } from "@/features/mantenimientos/types";
import { ApiError } from "@/lib/httpClient";
import { Button } from "@/shared/components/ui/button";
import { Checkbox } from "@/shared/components/ui/checkbox";
import { Input } from "@/shared/components/ui/input";
import { Select } from "@/shared/components/ui/select";
import { Skeleton } from "@/shared/components/ui/skeleton";

import {
  useActualizarMapeoEstadosMantenimiento,
  useActualizarPoliticaPassword,
  useActualizarUmbrales,
  useConfiguracion,
} from "../hooks/useConfiguracion";
import type { EstadoOperativoResultante, MapeoEstadosMantenimiento, PoliticaPassword } from "../types";

const POLITICA_DEFECTO: Required<PoliticaPassword> = {
  longitud_minima: 10,
  requiere_mayuscula: true,
  requiere_minuscula: true,
  requiere_digito: true,
  requiere_simbolo: true,
};

const MAPEO_DEFECTO: MapeoEstadosMantenimiento = {
  correctivo: "fuera_de_servicio",
  calibracion_correctiva: "fuera_de_servicio",
  preventivo: "en_mantenimiento",
  predictivo: "en_mantenimiento",
};

const ETIQUETAS_ESTADO_RESULTANTE: Record<EstadoOperativoResultante, string> = {
  fuera_de_servicio: "Fuera de servicio",
  en_mantenimiento: "En mantenimiento",
};

export function AlertasSection() {
  const { data: config, isLoading } = useConfiguracion();
  const actualizarUmbrales = useActualizarUmbrales();
  const actualizarPolitica = useActualizarPoliticaPassword();
  const actualizarMapeo = useActualizarMapeoEstadosMantenimiento();

  const [calibracion, setCalibracion] = useState(30);
  const [mantenimiento, setMantenimiento] = useState(15);
  const [documento, setDocumento] = useState(30);
  const [retencionPapelera, setRetencionPapelera] = useState(30);
  const [erroresCampoUmbrales, setErroresCampoUmbrales] = useState<{
    calibracion?: string;
    mantenimiento?: string;
    documento?: string;
    retencionPapelera?: string;
  }>({});
  const [errorUmbrales, setErrorUmbrales] = useState<string | null>(null);
  const [exitoUmbrales, setExitoUmbrales] = useState(false);

  const [politicaPersonalizada, setPoliticaPersonalizada] = useState(false);
  const [politica, setPolitica] = useState<Required<PoliticaPassword>>(POLITICA_DEFECTO);
  const [errorPolitica, setErrorPolitica] = useState<string | null>(null);
  const [exitoPolitica, setExitoPolitica] = useState(false);

  const [mapeo, setMapeo] = useState<MapeoEstadosMantenimiento>(MAPEO_DEFECTO);
  const [errorMapeo, setErrorMapeo] = useState<string | null>(null);
  const [exitoMapeo, setExitoMapeo] = useState(false);

  useEffect(() => {
    if (!config) return;
    setCalibracion(config.umbral_alerta_calibracion_dias);
    setMantenimiento(config.umbral_alerta_mantenimiento_dias);
    setDocumento(config.umbral_alerta_documento_dias);
    setRetencionPapelera(config.dias_retencion_papelera_documentos);
    setPoliticaPersonalizada(config.politica_password !== null);
    if (config.politica_password) {
      setPolitica({ ...POLITICA_DEFECTO, ...config.politica_password });
    }
    setMapeo({ ...MAPEO_DEFECTO, ...config.mapeo_estados_mantenimiento });
  }, [config]);

  async function guardarUmbrales() {
    setExitoUmbrales(false);
    setErrorUmbrales(null);

    const mensajeInvalido = "Debe ser un número entero positivo.";
    const errores: typeof erroresCampoUmbrales = {};
    if (calibracion <= 0) errores.calibracion = mensajeInvalido;
    if (mantenimiento <= 0) errores.mantenimiento = mensajeInvalido;
    if (documento <= 0) errores.documento = mensajeInvalido;
    if (retencionPapelera <= 0) errores.retencionPapelera = mensajeInvalido;
    setErroresCampoUmbrales(errores);
    if (Object.keys(errores).length > 0) return;

    try {
      await actualizarUmbrales.mutateAsync({
        umbral_alerta_calibracion_dias: calibracion,
        umbral_alerta_mantenimiento_dias: mantenimiento,
        umbral_alerta_documento_dias: documento,
        dias_retencion_papelera_documentos: retencionPapelera,
      });
      setExitoUmbrales(true);
    } catch (err) {
      setErrorUmbrales(err instanceof ApiError ? err.message : "No se pudieron guardar los umbrales.");
    }
  }

  async function guardarPolitica() {
    setExitoPolitica(false);
    setErrorPolitica(null);
    try {
      await actualizarPolitica.mutateAsync(politicaPersonalizada ? politica : null);
      setExitoPolitica(true);
    } catch (err) {
      setErrorPolitica(err instanceof ApiError ? err.message : "No se pudo guardar la política de contraseña.");
    }
  }

  async function guardarMapeo() {
    setExitoMapeo(false);
    setErrorMapeo(null);
    try {
      await actualizarMapeo.mutateAsync(mapeo);
      setExitoMapeo(true);
    } catch (err) {
      setErrorMapeo(err instanceof ApiError ? err.message : "No se pudo guardar la configuración de estados.");
    }
  }

  if (isLoading) {
    return (
      <div className="max-w-xl space-y-2">
        <Skeleton className="h-11 w-full" />
        <Skeleton className="h-11 w-full" />
        <Skeleton className="h-11 w-full" />
      </div>
    );
  }

  return (
    <div className="max-w-xl space-y-8">
      <section>
        <h2 className="mb-1 flex items-center gap-2 font-display text-base font-semibold text-ink">
          <Bell className="h-4 w-4 text-primary-900" aria-hidden="true" />
          Umbrales de alerta
        </h2>
        <p className="mb-4 text-sm text-ink-soft">
          Días de anticipación antes del vencimiento para marcar una calibración, mantenimiento o documento
          como "próximo a vencer".
        </p>
        <div className="grid grid-cols-1 gap-x-4 sm:grid-cols-3">
          <Input
            label="Calibraciones (días)"
            type="number"
            min={1}
            value={calibracion}
            onChange={(e) => setCalibracion(Number(e.target.value))}
            error={erroresCampoUmbrales.calibracion}
          />
          <Input
            label="Mantenimientos (días)"
            type="number"
            min={1}
            value={mantenimiento}
            onChange={(e) => setMantenimiento(Number(e.target.value))}
            error={erroresCampoUmbrales.mantenimiento}
          />
          <Input
            label="Documentos (días)"
            type="number"
            min={1}
            value={documento}
            onChange={(e) => setDocumento(Number(e.target.value))}
            error={erroresCampoUmbrales.documento}
          />
        </div>
        <p className="mb-1 mt-2 text-xs font-semibold text-ink-soft">
          Retención de la papelera de documentos (RN-DOC-03)
        </p>
        <div className="max-w-[calc((100%-2rem)/3)]">
          <Input
            label="Días antes de purgar"
            type="number"
            min={1}
            value={retencionPapelera}
            onChange={(e) => setRetencionPapelera(Number(e.target.value))}
            error={erroresCampoUmbrales.retencionPapelera}
          />
        </div>
        {errorUmbrales && (
          <p role="alert" aria-live="polite" className="mb-3 text-sm font-medium text-danger">
            {errorUmbrales}
          </p>
        )}
        {exitoUmbrales && (
          <p role="status" aria-live="polite" className="mb-3 text-sm font-medium text-[#065F46]">
            Umbrales actualizados.
          </p>
        )}
        <Button size="sm" cargando={actualizarUmbrales.isPending} onClick={guardarUmbrales}>
          Guardar umbrales
        </Button>
      </section>

      <section className="border-t border-border pt-6">
        <h2 className="mb-1 flex items-center gap-2 font-display text-base font-semibold text-ink">
          <ShieldCheck className="h-4 w-4 text-primary-900" aria-hidden="true" />
          Política de contraseña
        </h2>
        <p className="mb-4 text-sm text-ink-soft">
          Reglas de complejidad exigidas al crear usuarios o cambiar contraseñas. Sin personalizar, se usa la
          política por defecto (mínimo 10 caracteres, mayúscula, minúscula, dígito y símbolo).
        </p>

        <Checkbox
          name="politica-personalizada"
          label="Usar una política personalizada para este laboratorio"
          checked={politicaPersonalizada}
          onChange={(e) => setPoliticaPersonalizada(e.target.checked)}
        />

        {politicaPersonalizada && (
          <div className="mt-4">
            <Input
              label="Longitud mínima"
              type="number"
              min={8}
              max={128}
              value={politica.longitud_minima}
              onChange={(e) => setPolitica((p) => ({ ...p, longitud_minima: Number(e.target.value) }))}
            />
            <div className="mb-4 flex flex-wrap gap-x-4 gap-y-2">
              <Checkbox
                name="requiere-mayuscula"
                label="Requiere mayúscula"
                checked={politica.requiere_mayuscula}
                onChange={(e) => setPolitica((p) => ({ ...p, requiere_mayuscula: e.target.checked }))}
              />
              <Checkbox
                name="requiere-minuscula"
                label="Requiere minúscula"
                checked={politica.requiere_minuscula}
                onChange={(e) => setPolitica((p) => ({ ...p, requiere_minuscula: e.target.checked }))}
              />
              <Checkbox
                name="requiere-digito"
                label="Requiere dígito"
                checked={politica.requiere_digito}
                onChange={(e) => setPolitica((p) => ({ ...p, requiere_digito: e.target.checked }))}
              />
              <Checkbox
                name="requiere-simbolo"
                label="Requiere símbolo"
                checked={politica.requiere_simbolo}
                onChange={(e) => setPolitica((p) => ({ ...p, requiere_simbolo: e.target.checked }))}
              />
            </div>
          </div>
        )}

        {errorPolitica && (
          <p role="alert" aria-live="polite" className="mb-3 text-sm font-medium text-danger">
            {errorPolitica}
          </p>
        )}
        {exitoPolitica && (
          <p role="status" aria-live="polite" className="mb-3 text-sm font-medium text-[#065F46]">
            Política de contraseña actualizada.
          </p>
        )}
        <Button size="sm" cargando={actualizarPolitica.isPending} onClick={guardarPolitica}>
          Guardar política
        </Button>
      </section>

      <section className="border-t border-border pt-6">
        <h2 className="mb-1 flex items-center gap-2 font-display text-base font-semibold text-ink">
          <Wrench className="h-4 w-4 text-primary-900" aria-hidden="true" />
          Estados de mantenimiento
        </h2>
        <p className="mb-4 text-sm text-ink-soft">
          Estado operativo que toma el equipo al iniciar cada tipo de mantenimiento (RN-MANT-01).
        </p>
        <div className="grid grid-cols-1 gap-x-4 sm:grid-cols-2">
          {TIPOS_MANTENIMIENTO.map((tipo) => (
            <Select
              key={tipo}
              label={ETIQUETAS_TIPO[tipo]}
              value={mapeo[tipo] ?? MAPEO_DEFECTO[tipo]}
              onChange={(e) =>
                setMapeo((actual) => ({
                  ...actual,
                  [tipo]: e.target.value as EstadoOperativoResultante,
                }))
              }
            >
              {(Object.keys(ETIQUETAS_ESTADO_RESULTANTE) as EstadoOperativoResultante[]).map((estado) => (
                <option key={estado} value={estado}>
                  {ETIQUETAS_ESTADO_RESULTANTE[estado]}
                </option>
              ))}
            </Select>
          ))}
        </div>
        {errorMapeo && (
          <p role="alert" aria-live="polite" className="mb-3 text-sm font-medium text-danger">
            {errorMapeo}
          </p>
        )}
        {exitoMapeo && (
          <p role="status" aria-live="polite" className="mb-3 text-sm font-medium text-[#065F46]">
            Configuración de estados actualizada.
          </p>
        )}
        <Button size="sm" cargando={actualizarMapeo.isPending} onClick={guardarMapeo}>
          Guardar estados
        </Button>
      </section>
    </div>
  );
}
