import { ArrowLeft, File, RotateCcw, Trash2 } from "lucide-react";
import { useNavigate } from "react-router";

import { Button } from "@/shared/components/ui/button";
import { EmptyState } from "@/shared/components/ui/empty-state";
import { Skeleton } from "@/shared/components/ui/skeleton";

import { usePapelera, useRestaurarDocumento } from "../hooks/useDocumentos";

export function PapeleraPage() {
  const navigate = useNavigate();
  const { data: documentos, isLoading } = usePapelera();
  const restaurar = useRestaurarDocumento();

  return (
    <div className="p-6 sm:p-8">
      <button
        type="button"
        onClick={() => navigate("/documentos")}
        className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-ink-soft hover:text-ink"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Volver a Documentos
      </button>

      <h1 className="mb-1 font-display text-2xl font-semibold text-ink">Papelera</h1>
      <p className="mb-6 text-sm text-ink-soft">
        Los documentos eliminados se conservan aquí y pueden restaurarse (RN-DOC-03).
      </p>

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </div>
      )}

      {!isLoading && documentos?.length === 0 && (
        <EmptyState icon={Trash2} title="La papelera está vacía" description="Aquí aparecerán los documentos que elimines." />
      )}

      {!!documentos?.length && (
        <ul className="divide-y divide-border overflow-hidden rounded-lg border border-border">
          {documentos.map((documento) => (
            <li key={documento.id} className="flex items-center gap-3 bg-surface px-4 py-3">
              <File className="h-5 w-5 flex-shrink-0 text-ink-soft" aria-hidden="true" />
              <span className="min-w-0 flex-1 truncate text-sm font-medium text-ink">{documento.nombre}</span>
              <Button
                variant="secondary"
                size="sm"
                cargando={restaurar.isPending}
                onClick={() => restaurar.mutate(documento.id)}
              >
                <RotateCcw className="h-4 w-4" aria-hidden="true" />
                Restaurar
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
