import { AlertTriangle, ChevronDown, ChevronRight, Plus, Users } from "lucide-react";
import { useState } from "react";

import { EmptyState } from "@/shared/components/ui/empty-state";
import { Button } from "@/shared/components/ui/button";
import { Skeleton } from "@/shared/components/ui/skeleton";

import { useCrearUsuario, useUsuarios } from "../hooks/useUsuarios";
import { ETIQUETAS_ROL, type DatosCrearUsuario } from "../types";
import { EstadoUsuarioBadge } from "./EstadoUsuarioBadge";
import { PanelUsuario } from "./PanelUsuario";
import { UsuarioFormulario } from "./UsuarioFormulario";

export function UsuariosListPage() {
  const [pagina, setPagina] = useState(1);
  const { data, isLoading, isError } = useUsuarios(pagina);
  const usuarios = data?.items;
  const totalPaginas = data ? Math.max(1, Math.ceil(data.total / data.tamano_pagina)) : 1;
  const crear = useCrearUsuario();
  const [mostrandoFormulario, setMostrandoFormulario] = useState(false);
  const [expandidoId, setExpandidoId] = useState<string | null>(null);

  async function crearUsuario(datos: DatosCrearUsuario) {
    await crear.mutateAsync(datos);
    setMostrandoFormulario(false);
  }

  return (
    <div className="p-6 sm:p-8">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="mb-1 font-display text-2xl font-semibold text-ink">Usuarios y roles</h1>
          <p className="text-sm text-ink-soft">Crea usuarios, asigna roles y gestiona sus sesiones activas.</p>
        </div>
        {!mostrandoFormulario && (
          <Button size="sm" onClick={() => setMostrandoFormulario(true)}>
            <Plus className="h-4 w-4" aria-hidden="true" />
            Nuevo usuario
          </Button>
        )}
      </div>

      {mostrandoFormulario && (
        <div className="mb-6">
          <UsuarioFormulario
            guardando={crear.isPending}
            onGuardar={crearUsuario}
            onCancelar={() => setMostrandoFormulario(false)}
          />
        </div>
      )}

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      )}

      {isError && (
        <EmptyState
          icon={AlertTriangle}
          title="No se pudo cargar el listado"
          description="Intenta de nuevo en unos segundos."
        />
      )}

      {!isLoading && !isError && usuarios?.length === 0 && (
        <EmptyState icon={Users} title="Sin usuarios" description="Crea el primer usuario del laboratorio." />
      )}

      {!isError && !!usuarios?.length && (
        <ul className="divide-y divide-border overflow-hidden rounded-lg border border-border">
          {usuarios.map((usuario) => {
            const expandido = expandidoId === usuario.id;
            return (
              <li key={usuario.id} className="bg-surface">
                <button
                  type="button"
                  onClick={() => setExpandidoId(expandido ? null : usuario.id)}
                  className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-surface-alt"
                  aria-expanded={expandido}
                >
                  <div className="flex min-w-0 items-center gap-2">
                    {expandido ? (
                      <ChevronDown className="h-4 w-4 flex-shrink-0 text-ink-soft" aria-hidden="true" />
                    ) : (
                      <ChevronRight className="h-4 w-4 flex-shrink-0 text-ink-soft" aria-hidden="true" />
                    )}
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-ink">{usuario.nombre_completo}</p>
                      <p className="truncate text-xs text-ink-soft">
                        {usuario.correo} ·{" "}
                        {usuario.roles.map((r) => ETIQUETAS_ROL[r] ?? r).join(", ") || "sin roles"}
                      </p>
                    </div>
                  </div>
                  <EstadoUsuarioBadge estado={usuario.estado} />
                </button>
                {expandido && <PanelUsuario usuario={usuario} />}
              </li>
            );
          })}
        </ul>
      )}

      {!isError && totalPaginas > 1 && (
        <div className="mt-5 flex items-center justify-center gap-3 text-sm text-ink-soft">
          <Button variant="secondary" size="sm" disabled={pagina <= 1} onClick={() => setPagina((p) => p - 1)}>
            Anterior
          </Button>
          <span>
            Página {pagina} de {totalPaginas}
          </span>
          <Button
            variant="secondary"
            size="sm"
            disabled={pagina >= totalPaginas}
            onClick={() => setPagina((p) => p + 1)}
          >
            Siguiente
          </Button>
        </div>
      )}
    </div>
  );
}
