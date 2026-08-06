import { ClipboardList, FileText, Gauge, ShieldCheck, Wrench } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Badge, type BadgeProps } from "@/shared/components/ui/badge";
import { Skeleton } from "@/shared/components/ui/skeleton";

import type { Kpis, SemaforoCalibracionAgregado } from "../types";

const ETIQUETA_SEMAFORO: Record<SemaforoCalibracionAgregado, string> = {
  normal: "Normal",
  atencion: "Atención",
  critico: "Crítico",
};
const VARIANTE_SEMAFORO: Record<SemaforoCalibracionAgregado, NonNullable<BadgeProps["variant"]>> = {
  normal: "success",
  atencion: "warning",
  critico: "danger",
};

function CardShell({
  icon: Icon,
  iconVariant,
  children,
}: {
  icon: LucideIcon;
  iconVariant: NonNullable<BadgeProps["variant"]>;
  children: React.ReactNode;
}) {
  const tonos: Record<string, string> = {
    neutral: "bg-surface-alt text-ink-soft",
    success: "bg-[#D1FAE5] text-[#065F46]",
    warning: "bg-[#FEF3C7] text-[#92400E]",
    danger: "bg-[#FEE2E2] text-[#991B1B]",
    info: "bg-[#DBEAFE] text-[#1E40AF]",
  };
  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border bg-surface p-4 transition-colors duration-base hover:border-primary-100">
      <div className={`flex h-8 w-8 items-center justify-center rounded-sm ${tonos[iconVariant]}`}>
        <Icon className="h-4 w-4" aria-hidden="true" />
      </div>
      {children}
    </div>
  );
}

export function KpiCards({ kpis, isLoading, isError }: { kpis?: Kpis; isLoading: boolean; isError: boolean }) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-32 w-full" />
        ))}
      </div>
    );
  }

  if (isError || !kpis) {
    return (
      <div className="rounded-md border border-border bg-surface p-6 text-center text-sm text-ink-soft">
        No se pudieron cargar los indicadores del laboratorio.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
      <CardShell icon={ClipboardList} iconVariant="neutral">
        <div>
          <p className="font-display text-2xl font-bold tabular-nums text-ink">
            {kpis.equipos_total} <span className="text-sm font-semibold text-ink-soft">equipos</span>
          </p>
          <p className="text-xs font-semibold text-ink-soft">Equipos activos</p>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-surface-alt">
          <div
            className="h-full rounded-full bg-success"
            style={{ width: `${kpis.equipos_porcentaje_operativo}%` }}
          />
        </div>
        <p className="text-[11px] text-ink-soft">{kpis.equipos_porcentaje_operativo}% operativos</p>
      </CardShell>

      <CardShell icon={ShieldCheck} iconVariant={VARIANTE_SEMAFORO[kpis.calibraciones_semaforo]}>
        <div className="flex items-start justify-between">
          <div>
            <p className="font-display text-2xl font-bold tabular-nums text-ink">
              {kpis.calibraciones_proximas_30_dias} <span className="text-sm font-semibold text-ink-soft">equipos</span>
            </p>
            <p className="text-xs font-semibold text-ink-soft">Próximas calibraciones</p>
          </div>
          <Badge variant={VARIANTE_SEMAFORO[kpis.calibraciones_semaforo]}>
            {ETIQUETA_SEMAFORO[kpis.calibraciones_semaforo]}
          </Badge>
        </div>
        <p className="text-[11px] text-ink-soft">En los próximos 30 días</p>
      </CardShell>

      <CardShell icon={FileText} iconVariant={kpis.documentos_vencidos > 0 ? "danger" : "neutral"}>
        <div>
          <p className="font-display text-2xl font-bold tabular-nums text-ink">
            {kpis.documentos_vencidos + kpis.documentos_por_vencer}{" "}
            <span className="text-sm font-semibold text-ink-soft">documentos</span>
          </p>
          <p className="text-xs font-semibold text-ink-soft">Documentación pendiente</p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {kpis.documentos_vencidos > 0 && <Badge variant="danger">{kpis.documentos_vencidos} vencidos</Badge>}
          {kpis.documentos_por_vencer > 0 && (
            <Badge variant="warning">{kpis.documentos_por_vencer} por vencer</Badge>
          )}
          {kpis.documentos_en_revision > 0 && (
            <Badge variant="neutral">{kpis.documentos_en_revision} en revisión</Badge>
          )}
        </div>
      </CardShell>

      <CardShell icon={Wrench} iconVariant="info">
        <div>
          <p className="font-display text-2xl font-bold tabular-nums text-ink">
            {kpis.mantenimientos_preventivos_proximos}{" "}
            <span className="text-sm font-semibold text-ink-soft">preventivos</span>
          </p>
          <p className="text-xs font-semibold text-ink-soft">Mantenimientos</p>
        </div>
        <p className="text-[11px] text-ink-soft">
          {kpis.mantenimientos_preventivos_proximos} preventivos próximos ·{" "}
          {kpis.mantenimientos_correctivos_abiertos} correctivos abiertos
        </p>
      </CardShell>

      <CardShell icon={Gauge} iconVariant="success">
        {kpis.cumplimiento_documental_pct === null ? (
          <div>
            <p className="font-display text-lg font-bold text-ink-soft">—</p>
            <p className="text-xs font-semibold text-ink-soft">
              Cumplimiento documental
              <br />
              <span className="font-normal text-[11px]">Aún no hay documentos registrados</span>
            </p>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <ComplianceGauge porcentaje={kpis.cumplimiento_documental_pct} />
            <div>
              <p className="font-display text-xl font-bold tabular-nums text-ink">
                {kpis.cumplimiento_documental_pct}%
              </p>
              <p className="text-xs font-semibold text-ink-soft">
                Cumplimiento
                <br />
                documental
              </p>
            </div>
          </div>
        )}
      </CardShell>
    </div>
  );
}

function ComplianceGauge({ porcentaje }: { porcentaje: number }) {
  const radio = 20;
  const circunferencia = 2 * Math.PI * radio;
  const offset = circunferencia * (1 - porcentaje / 100);
  const color = porcentaje >= 90 ? "var(--success)" : porcentaje >= 70 ? "var(--warning)" : "var(--danger)";

  return (
    <svg width="52" height="52" viewBox="0 0 52 52" role="img" aria-label={`Cumplimiento documental: ${porcentaje}%`}>
      <circle cx="26" cy="26" r={radio} fill="none" stroke="var(--border)" strokeWidth="6" />
      <circle
        cx="26"
        cy="26"
        r={radio}
        fill="none"
        stroke={color}
        strokeWidth="6"
        strokeLinecap="round"
        strokeDasharray={circunferencia}
        strokeDashoffset={offset}
        transform="rotate(-90 26 26)"
      />
    </svg>
  );
}
