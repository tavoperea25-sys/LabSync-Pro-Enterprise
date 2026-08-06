import type { LucideIcon } from "lucide-react";
import {
  Bell,
  Calendar,
  ClipboardList,
  FileBarChart,
  FileText,
  Gauge,
  History,
  Settings,
  ShieldCheck,
  Users,
  Wrench,
} from "lucide-react";

/** Espejo de docs/08-sitemap.md — ítems a los que un rol no tiene acceso
 * simplemente no se renderizan (no aparecen deshabilitados). */
export interface NavItem {
  label: string;
  path: string;
  icon: LucideIcon;
  roles: string[];
}

const TODOS = ["administrador", "director_tecnico", "calidad", "metrologia", "tecnico", "consulta"];

export const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", path: "/dashboard", icon: Gauge, roles: TODOS },
  { label: "Equipos", path: "/equipos", icon: ClipboardList, roles: TODOS },
  { label: "Documentos", path: "/documentos", icon: FileText, roles: TODOS },
  { label: "Calibraciones", path: "/calibraciones", icon: ShieldCheck, roles: TODOS },
  { label: "Mantenimientos", path: "/mantenimientos", icon: Wrench, roles: TODOS },
  { label: "Calendario", path: "/calendario", icon: Calendar, roles: TODOS },
  { label: "Alertas", path: "/alertas", icon: Bell, roles: TODOS },
  {
    label: "Reportes",
    path: "/reportes",
    icon: FileBarChart,
    // Espejo de MATRIZ_ROL_PERMISOS["reportes.generar"] en
    // app/seeds/seed_roles_permisos.py — técnico y consulta no lo tienen.
    roles: ["administrador", "director_tecnico", "calidad", "metrologia"],
  },
  { label: "Auditoría", path: "/auditoria", icon: History, roles: ["administrador", "calidad"] },
  { label: "Usuarios", path: "/usuarios", icon: Users, roles: ["administrador"] },
  // RF-CFG-01: cualquier usuario autenticado gestiona su propio perfil ahí
  // — las secciones de administración (laboratorio/alertas/categorías)
  // se ocultan dentro de la página misma según el rol, no aquí.
  { label: "Configuración", path: "/configuracion", icon: Settings, roles: TODOS },
];

export function navItemsParaRoles(rolesUsuario: string[]): NavItem[] {
  return NAV_ITEMS.filter((item) => item.roles.some((r) => rolesUsuario.includes(r)));
}
