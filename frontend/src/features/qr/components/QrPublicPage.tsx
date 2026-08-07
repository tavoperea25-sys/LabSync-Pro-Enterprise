import { zodResolver } from "@hookform/resolvers/zod";
import { AlertTriangle, CheckCircle2, FlaskConical, QrCode } from "lucide-react";
import { useForm } from "react-hook-form";
import { useParams } from "react-router";
import { z } from "zod";

import { ApiError } from "@/lib/httpClient";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Textarea } from "@/shared/components/ui/textarea";

import { EquipoEstadoBadge } from "@/features/equipos/components/EquipoEstadoBadge";

import { useEquipoPorQr, useReportarIncidencia } from "../hooks/useQrPublico";

const esquemaIncidencia = z.object({
  descripcion: z.string().min(1, "Describe brevemente la incidencia.").max(1000),
  contacto_nombre: z.string().max(150).optional(),
  contacto_medio: z.string().max(150).optional(),
});

type FormularioIncidencia = z.infer<typeof esquemaIncidencia>;

export function QrPublicPage() {
  const { token } = useParams<{ token: string }>();
  const { data: equipo, isLoading, isError } = useEquipoPorQr(token);
  const reportar = useReportarIncidencia(token ?? "");

  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormularioIncidencia>({ resolver: zodResolver(esquemaIncidencia) });

  async function onSubmit(datos: FormularioIncidencia) {
    try {
      await reportar.mutateAsync(datos);
      reset();
    } catch (error) {
      if (error instanceof ApiError && error.status === 429) {
        setError("root", { message: "Demasiados reportes en poco tiempo. Intenta de nuevo en unos minutos." });
      } else if (error instanceof ApiError) {
        setError("root", { message: error.message });
      }
    }
  }

  return (
    <div className="min-h-dvh bg-surface-alt px-4 py-10 sm:py-16">
      <div className="mx-auto max-w-md">
        <div className="mb-6 flex items-center justify-center gap-2 text-primary-900">
          <FlaskConical className="h-6 w-6" aria-hidden="true" />
          <span className="font-display text-lg font-semibold">LabSync Pro</span>
        </div>

        <div className="rounded-lg border border-border bg-surface p-6 shadow-sm">
          {isLoading && <p className="text-center text-sm text-ink-soft">Cargando información del equipo…</p>}

          {!isLoading && (isError || !equipo) && (
            <div className="flex flex-col items-center gap-2 py-6 text-center">
              <QrCode className="h-10 w-10 text-ink-soft" aria-hidden="true" />
              <h1 className="font-display text-base font-semibold text-ink">Código QR no válido</h1>
              <p className="text-sm text-ink-soft">
                Este código no corresponde a ningún equipo registrado o fue revocado.
              </p>
            </div>
          )}

          {!isLoading && equipo && (
            <>
              {equipo.foto_url && (
                <img
                  src={equipo.foto_url}
                  alt={`Fotografía de ${equipo.nombre}`}
                  className="mb-4 h-40 w-full rounded-md border border-border object-cover"
                />
              )}
              <p className="text-xs font-semibold text-ink-soft">{equipo.codigo_interno}</p>
              <h1 className="font-display text-xl font-semibold text-ink">{equipo.nombre}</h1>
              <div className="mt-2">
                <EquipoEstadoBadge estado={equipo.estado_operativo} />
              </div>

              {equipo.dado_de_baja && (
                <div className="mt-4 flex items-start gap-2 rounded-md border border-danger/30 bg-[#FEF2F2] p-3">
                  <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-danger" aria-hidden="true" />
                  <p className="text-sm text-[#991B1B]">Este equipo fue dado de baja y ya no está en servicio.</p>
                </div>
              )}

              <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 border-t border-border pt-4">
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-ink-soft">Marca</dt>
                  <dd className="mt-0.5 text-sm text-ink">{equipo.marca || "—"}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-ink-soft">Modelo</dt>
                  <dd className="mt-0.5 text-sm text-ink">{equipo.modelo || "—"}</dd>
                </div>
              </dl>

              <div className="mt-6 border-t border-border pt-5">
                <h2 className="mb-1 text-sm font-semibold text-ink">Reportar una incidencia</h2>
                <p className="mb-4 text-xs text-ink-soft">
                  ¿Notas algo anormal en este equipo? Cuéntanos qué pasa; el laboratorio lo revisará.
                </p>

                {reportar.isSuccess ? (
                  <div className="flex items-start gap-2 rounded-md border border-primary-tint bg-primary-tint p-3">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-primary-900" aria-hidden="true" />
                    <p className="text-sm text-primary-900">
                      Gracias, tu reporte fue registrado. El equipo responsable le dará seguimiento.
                    </p>
                  </div>
                ) : (
                  <form onSubmit={handleSubmit(onSubmit)} noValidate>
                    <Textarea
                      label="¿Qué está pasando?"
                      error={errors.descripcion?.message}
                      {...register("descripcion")}
                    />
                    <Input
                      label="Tu nombre (opcional)"
                      error={errors.contacto_nombre?.message}
                      {...register("contacto_nombre")}
                    />
                    <Input
                      label="Teléfono o correo (opcional)"
                      error={errors.contacto_medio?.message}
                      {...register("contacto_medio")}
                    />

                    {errors.root?.message && (
                      <p role="alert" aria-live="polite" className="mb-4 text-sm font-medium text-danger">
                        {errors.root.message}
                      </p>
                    )}

                    <Button type="submit" cargando={isSubmitting} className="w-full">
                      Enviar reporte
                    </Button>
                  </form>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
