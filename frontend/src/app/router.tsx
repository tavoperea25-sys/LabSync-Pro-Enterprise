import { lazy, type ReactNode } from "react";
import { createBrowserRouter, createRoutesFromElements, Navigate, Route } from "react-router";

import { AppShell } from "./AppShell";
import { ProtectedRoute } from "./ProtectedRoute";
import { RouteErrorPage } from "./RouteErrorPage";

// RNF-PERF — code-splitting por ruta (auditoría 2026-07-31, hallazgo I8):
// antes, las 18 páginas se importaban de forma estática y terminaban todas
// en el único bundle inicial — un usuario que solo necesitaba `/login`
// descargaba también Reportes, Auditoría, Calendario, QR público, etc.
// `React.lazy` + `Suspense` (ver `RouteFallback` en `App.tsx`, y el límite
// adicional dentro de `AppShell` para que la navegación no desaparezca al
// cambiar de ruta) hace que cada página sea su propio chunk, descargado
// solo cuando se visita. Los componentes se exportan con nombre (no
// `export default`) en todo el proyecto — de ahí el `.then(...)` que
// adapta cada import al formato `{ default }` que `React.lazy` requiere.
const AlertasPage = lazy(() =>
  import("@/features/alertas/components/AlertasPage").then((m) => ({ default: m.AlertasPage })),
);
const AuditoriaPage = lazy(() =>
  import("@/features/auditoria/components/AuditoriaPage").then((m) => ({ default: m.AuditoriaPage })),
);
const CambiarPasswordObligatorioPage = lazy(() =>
  import("@/features/auth/components/CambiarPasswordObligatorioPage").then((m) => ({
    default: m.CambiarPasswordObligatorioPage,
  })),
);
const LoginPage = lazy(() =>
  import("@/features/auth/components/LoginPage").then((m) => ({ default: m.LoginPage })),
);
const CalendarioPage = lazy(() =>
  import("@/features/calendario/components/CalendarioPage").then((m) => ({ default: m.CalendarioPage })),
);
const CriticosPage = lazy(() =>
  import("@/features/calibraciones/components/CriticosPage").then((m) => ({ default: m.CriticosPage })),
);
const ConfiguracionPage = lazy(() =>
  import("@/features/configuracion/components/ConfiguracionPage").then((m) => ({
    default: m.ConfiguracionPage,
  })),
);
const DashboardPage = lazy(() =>
  import("@/features/dashboard/DashboardPage").then((m) => ({ default: m.DashboardPage })),
);
const DocumentoDetailPage = lazy(() =>
  import("@/features/documentos/components/DocumentoDetailPage").then((m) => ({
    default: m.DocumentoDetailPage,
  })),
);
const DocumentosPage = lazy(() =>
  import("@/features/documentos/components/DocumentosPage").then((m) => ({ default: m.DocumentosPage })),
);
const PapeleraPage = lazy(() =>
  import("@/features/documentos/components/PapeleraPage").then((m) => ({ default: m.PapeleraPage })),
);
const EquipoDetailPage = lazy(() =>
  import("@/features/equipos/components/EquipoDetailPage").then((m) => ({ default: m.EquipoDetailPage })),
);
const EquipoFormPage = lazy(() =>
  import("@/features/equipos/components/EquipoFormPage").then((m) => ({ default: m.EquipoFormPage })),
);
const EquiposListPage = lazy(() =>
  import("@/features/equipos/components/EquiposListPage").then((m) => ({ default: m.EquiposListPage })),
);
const MantenimientosListPage = lazy(() =>
  import("@/features/mantenimientos/components/MantenimientosListPage").then((m) => ({
    default: m.MantenimientosListPage,
  })),
);
const QrPublicPage = lazy(() =>
  import("@/features/qr/components/QrPublicPage").then((m) => ({ default: m.QrPublicPage })),
);
const ReportesPage = lazy(() =>
  import("@/features/reportes/components/ReportesPage").then((m) => ({ default: m.ReportesPage })),
);
const UsuariosListPage = lazy(() =>
  import("@/features/usuarios/components/UsuariosListPage").then((m) => ({ default: m.UsuariosListPage })),
);

function conShell(contenido: ReactNode) {
  return (
    <ProtectedRoute>
      <AppShell>{contenido}</AppShell>
    </ProtectedRoute>
  );
}

// Ruta raíz sin `path` ni `element` propios (layout "pathless"): no aporta
// ningún segmento a la URL (cada ruta hija sigue siendo exactamente la
// misma ruta absoluta de siempre, p. ej. "/login"), solo agrupa todo bajo
// un único `errorElement` — sin esto, un error no capturado en el render
// de cualquier ruta cae en la pantalla de error por defecto del data
// router (en inglés y, en desarrollo, con el detalle técnico del error).
export const router = createBrowserRouter(
  createRoutesFromElements(
    <Route errorElement={<RouteErrorPage />}>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/qr/:token" element={<QrPublicPage />} />
      <Route
        path="/cambiar-password"
        element={
          <ProtectedRoute>
            <CambiarPasswordObligatorioPage />
          </ProtectedRoute>
        }
      />
      <Route path="/dashboard" element={conShell(<DashboardPage />)} />

      <Route path="/documentos" element={conShell(<DocumentosPage />)} />
      <Route path="/documentos/papelera" element={conShell(<PapeleraPage />)} />
      <Route path="/documentos/:id" element={conShell(<DocumentoDetailPage />)} />

      <Route path="/calibraciones" element={conShell(<CriticosPage />)} />

      <Route path="/mantenimientos" element={conShell(<MantenimientosListPage />)} />

      <Route path="/alertas" element={conShell(<AlertasPage />)} />

      <Route path="/calendario" element={conShell(<CalendarioPage />)} />

      <Route path="/reportes" element={conShell(<ReportesPage />)} />

      <Route path="/auditoria" element={conShell(<AuditoriaPage />)} />
      <Route path="/usuarios" element={conShell(<UsuariosListPage />)} />

      <Route path="/equipos" element={conShell(<EquiposListPage />)} />
      <Route path="/equipos/nuevo" element={conShell(<EquipoFormPage />)} />
      <Route path="/equipos/:id" element={conShell(<EquipoDetailPage />)} />
      <Route path="/equipos/:id/editar" element={conShell(<EquipoFormPage />)} />

      <Route path="/configuracion" element={conShell(<ConfiguracionPage />)} />

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Route>,
  ),
);
