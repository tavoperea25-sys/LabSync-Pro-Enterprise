import { Building2, Download, Upload } from "lucide-react";
import { useEffect, useState } from "react";

import { ApiError } from "@/lib/httpClient";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { SubirFotoConPreview } from "@/shared/components/ui/subir-foto-con-preview";

import * as api from "../api/configuracionApi";
import { useActualizarInstitucion, useExportarDatosTenant, useInstitucion } from "../hooks/useConfiguracion";

export function LaboratorioSection() {
  const { data: institucion, isLoading } = useInstitucion();
  const actualizar = useActualizarInstitucion();
  const exportarDatos = useExportarDatosTenant();
  const [errorExportacion, setErrorExportacion] = useState<string | null>(null);

  const [nombre, setNombre] = useState("");
  // object_key que se envía al guardar: se inicializa con el logo actual y
  // solo cambia si el usuario sube uno nuevo — así "guardar" sin tocar el
  // logo no lo borra (ver InstitucionOut.logo_object_key en el backend).
  const [logoObjectKey, setLogoObjectKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exito, setExito] = useState(false);

  useEffect(() => {
    if (!institucion) return;
    setNombre(institucion.nombre);
    setLogoObjectKey(institucion.logo_object_key);
  }, [institucion]);

  async function subirLogo(archivo: File): Promise<string> {
    const { url_subida, object_key } = await api.solicitarUrlLogo(archivo.name, archivo.type, archivo.size);
    await fetch(url_subida, { method: "PUT", body: archivo, headers: { "Content-Type": archivo.type } });
    return object_key;
  }

  async function guardar() {
    if (!nombre.trim()) {
      setError("El nombre del laboratorio es obligatorio.");
      return;
    }
    setError(null);
    setExito(false);
    try {
      await actualizar.mutateAsync({ nombre: nombre.trim(), logoObjectKey });
      setExito(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar el laboratorio.");
    }
  }

  async function exportar() {
    setErrorExportacion(null);
    try {
      await exportarDatos.mutateAsync();
    } catch (err) {
      setErrorExportacion(err instanceof ApiError ? err.message : "No se pudo generar la exportación.");
    }
  }

  if (isLoading) {
    return (
      <div className="max-w-xl space-y-3">
        <Skeleton className="h-11 w-full" />
        <Skeleton className="h-20 w-20 rounded-full" />
      </div>
    );
  }

  return (
    <div className="max-w-xl">
      <h2 className="mb-1 flex items-center gap-2 font-display text-base font-semibold text-ink">
        <Building2 className="h-4 w-4 text-primary-900" aria-hidden="true" />
        Datos institucionales
      </h2>
      <p className="mb-4 text-sm text-ink-soft">
        Nombre y logo del laboratorio, usados en la interfaz y en los reportes generados.
      </p>

      <Input label="Nombre del laboratorio" value={nombre} onChange={(e) => setNombre(e.target.value)} />

      <SubirFotoConPreview
        etiqueta="Logo"
        urlActual={institucion?.logo_url ?? null}
        onSubir={subirLogo}
        onSubidoExitosamente={setLogoObjectKey}
        iconoVacio={Building2}
        iconoBoton={Upload}
        textoBoton="Subir logo"
        textoAyuda="PNG, JPG o WEBP. Máximo 2MB."
        altTexto="Logo del laboratorio"
        forma="circulo"
        tamano="md"
        mensajeErrorDefecto="No se pudo subir el logo."
      />

      {error && (
        <p role="alert" aria-live="polite" className="mb-3 text-sm font-medium text-danger">
          {error}
        </p>
      )}
      {exito && (
        <p role="status" aria-live="polite" className="mb-3 text-sm font-medium text-[#065F46]">
          Datos institucionales actualizados.
        </p>
      )}

      <Button size="sm" cargando={actualizar.isPending} onClick={guardar}>
        Guardar cambios
      </Button>

      <div className="mt-8 border-t border-border pt-6">
        <h2 className="mb-1 flex items-center gap-2 font-display text-base font-semibold text-ink">
          <Download className="h-4 w-4 text-primary-900" aria-hidden="true" />
          Exportar datos del laboratorio
        </h2>
        <p className="mb-4 text-sm text-ink-soft">
          Descarga un ZIP con los datos de equipos, documentos, calibraciones, mantenimientos, usuarios,
          categorías y áreas en formato CSV — no incluye archivos adjuntos ni contraseñas.
        </p>
        {errorExportacion && (
          <p role="alert" aria-live="polite" className="mb-3 text-sm font-medium text-danger">
            {errorExportacion}
          </p>
        )}
        <Button size="sm" variant="secondary" cargando={exportarDatos.isPending} onClick={exportar}>
          <Download className="h-4 w-4" aria-hidden="true" />
          Exportar todos los datos
        </Button>
      </div>
    </div>
  );
}
