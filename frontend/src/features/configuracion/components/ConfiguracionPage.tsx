import { Bell, Building2, Layers, User } from "lucide-react";
import { useState } from "react";

import { useAuth } from "@/features/auth/hooks/AuthProvider";
import { cn } from "@/shared/lib/cn";

import { AlertasSection } from "./AlertasSection";
import { CategoriasAreasSection } from "./CategoriasAreasSection";
import { LaboratorioSection } from "./LaboratorioSection";
import { PerfilSection } from "./PerfilSection";

type Seccion = "perfil" | "laboratorio" | "alertas" | "referencias";

export function ConfiguracionPage() {
  const { usuario } = useAuth();
  const esAdmin = usuario?.roles.includes("administrador") ?? false;
  const [seccion, setSeccion] = useState<Seccion>("perfil");

  const secciones: { id: Seccion; etiqueta: string; icon: typeof User }[] = [
    { id: "perfil", etiqueta: "Mi perfil", icon: User },
    ...(esAdmin
      ? ([
          { id: "laboratorio", etiqueta: "Laboratorio", icon: Building2 },
          { id: "alertas", etiqueta: "Alertas", icon: Bell },
          { id: "referencias", etiqueta: "Categorías y áreas", icon: Layers },
        ] as const)
      : []),
  ];

  return (
    <div className="p-6 sm:p-8">
      <div className="mb-6">
        <h1 className="mb-1 font-display text-2xl font-semibold text-ink">Configuración</h1>
        <p className="text-sm text-ink-soft">
          {esAdmin
            ? "Tu perfil, datos del laboratorio, umbrales de alerta y categorías/áreas de equipo."
            : "Tu perfil y preferencias de cuenta."}
        </p>
      </div>

      <nav aria-label="Secciones de configuración" className="mb-8 flex flex-wrap gap-2 border-b border-border">
        {secciones.map(({ id, etiqueta, icon: Icon }) => (
          <button
            key={id}
            type="button"
            aria-current={seccion === id ? "page" : undefined}
            onClick={() => setSeccion(id)}
            className={cn(
              "flex items-center gap-2 border-b-2 px-3 py-2.5 text-sm font-semibold transition-colors duration-fast",
              seccion === id
                ? "border-primary-900 text-primary-900"
                : "border-transparent text-ink-soft hover:text-ink",
            )}
          >
            <Icon className="h-4 w-4" aria-hidden="true" />
            {etiqueta}
          </button>
        ))}
      </nav>

      {seccion === "perfil" && <PerfilSection />}
      {seccion === "laboratorio" && esAdmin && <LaboratorioSection />}
      {seccion === "alertas" && esAdmin && <AlertasSection />}
      {seccion === "referencias" && esAdmin && <CategoriasAreasSection />}
    </div>
  );
}
