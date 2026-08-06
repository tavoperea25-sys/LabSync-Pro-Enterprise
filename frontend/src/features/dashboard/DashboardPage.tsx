import { useAuth } from "@/features/auth/hooks/AuthProvider";
import { MisMantenimientosHoyWidget } from "@/features/mantenimientos/components/MisMantenimientosHoyWidget";

import { ActivityTimeline } from "./components/ActivityTimeline";
import { AiAssistantCard } from "./components/AiAssistantCard";
import { AlertsSummary } from "./components/AlertsSummary";
import { CalibrationAgenda } from "./components/CalibrationAgenda";
import { CriticalEquipmentTable } from "./components/CriticalEquipmentTable";
import { EquipmentStatusDonut } from "./components/EquipmentStatusDonut";
import { KpiCards } from "./components/KpiCards";
import { QuickActions } from "./components/QuickActions";
import { useEquiposCriticos, useKpis } from "./hooks/useDashboard";

// Espejo de MATRIZ_ROL_PERMISOS["auditoria.ver"] en
// app/seeds/seed_roles_permisos.py — mismos roles que ven "Auditoría" en el
// sidebar (ver navigation.ts), aquí se usa para no pedir el widget de
// actividad reciente si el backend de todos modos respondería 403.
const ROLES_CON_AUDITORIA = ["administrador", "director_tecnico", "calidad"];

function saludo(): string {
  const hora = new Date().getHours();
  if (hora < 12) return "Buenos días";
  if (hora < 19) return "Buenas tardes";
  return "Buenas noches";
}

export function DashboardPage() {
  const { usuario } = useAuth();
  const { data: kpis, isLoading: cargandoKpis, isError: errorKpis } = useKpis();
  const { data: equiposCriticos } = useEquiposCriticos(10);
  const puedeVerAuditoria = (usuario?.roles ?? []).some((r) => ROLES_CON_AUDITORIA.includes(r));

  const fechaHoy = new Date().toLocaleDateString("es-CO", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  return (
    <div className="p-6 sm:p-8">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold capitalize text-ink">
            {saludo()}, {usuario?.nombre_completo?.split(" ")[0] ?? "Administrador"}
          </h1>
          <p className="mt-1 text-sm text-ink-soft">Resumen operativo del laboratorio</p>
        </div>
        <div className="flex flex-col items-end gap-1.5">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-[#D1FAE5] px-3 py-1 text-xs font-semibold text-[#065F46]">
            <span className="h-1.5 w-1.5 rounded-full bg-success" aria-hidden="true" />
            Laboratorio operativo
          </span>
          <span className="text-xs capitalize text-ink-soft">{fechaHoy}</span>
        </div>
      </div>

      <div className="mb-4">
        <KpiCards kpis={kpis} isLoading={cargandoKpis} isError={errorKpis} />
      </div>

      <div className="mb-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
        <EquipmentStatusDonut kpis={kpis} isLoading={cargandoKpis} />
        <CalibrationAgenda />
      </div>

      <div className="mb-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
        <AlertsSummary />
        <ActivityTimeline puedeVer={puedeVerAuditoria} />
      </div>

      <div className="mb-4">
        <QuickActions />
      </div>

      <MisMantenimientosHoyWidget />

      <div className="my-4">
        <AiAssistantCard kpis={kpis} equiposCriticos={equiposCriticos} />
      </div>

      <CriticalEquipmentTable />
    </div>
  );
}
