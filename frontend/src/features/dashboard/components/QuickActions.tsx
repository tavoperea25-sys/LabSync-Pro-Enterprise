import { ClipboardList, FileUp, ShieldCheck, Wrench, Zap, FileBarChart } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Link } from "react-router";

const ACCIONES: { label: string; hint: string; icon: LucideIcon; to: string }[] = [
  { label: "Registrar equipo", hint: "Alta en el inventario", icon: ClipboardList, to: "/equipos/nuevo" },
  { label: "Nueva calibración", hint: "Registrar resultado", icon: ShieldCheck, to: "/calibraciones" },
  { label: "Subir documento", hint: "POE, certificado…", icon: FileUp, to: "/documentos" },
  { label: "Crear mantenimiento", hint: "Preventivo o correctivo", icon: Wrench, to: "/mantenimientos" },
  { label: "Generar reporte", hint: "PDF / Excel", icon: FileBarChart, to: "/reportes" },
];

export function QuickActions() {
  return (
    <section>
      <h2 className="mb-2.5 flex items-center gap-2 text-sm font-semibold text-ink">
        <Zap className="h-4 w-4 text-ink-soft" aria-hidden="true" />
        Acciones rápidas
      </h2>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {ACCIONES.map(({ label, hint, icon: Icon, to }) => (
          <Link
            key={label}
            to={to}
            className="flex flex-col items-start gap-2.5 rounded-lg border border-border bg-surface p-4 transition-all duration-base hover:-translate-y-0.5 hover:border-primary-100"
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-sm bg-primary-tint text-primary-900">
              <Icon className="h-[18px] w-[18px]" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm font-semibold text-ink">{label}</p>
              <p className="text-[11px] text-ink-soft">{hint}</p>
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}
