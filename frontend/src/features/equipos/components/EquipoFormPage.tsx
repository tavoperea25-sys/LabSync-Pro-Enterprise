import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, Camera, FileText, Save } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useParams } from "react-router";
import { z } from "zod";

import { ApiError } from "@/lib/httpClient";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { LinkButton } from "@/shared/components/ui/link-button";
import { Select } from "@/shared/components/ui/select";
import { SubirFotoConPreview } from "@/shared/components/ui/subir-foto-con-preview";
import { Textarea } from "@/shared/components/ui/textarea";

import { solicitarUrlFoto, solicitarUrlManual } from "../api/equiposApi";
import { useActualizarEquipo, useAreas, useCategorias, useCrearEquipo, useEquipo } from "../hooks/useEquipos";
import { ESTADOS_OPERATIVOS, ETIQUETAS_ESTADO } from "../types";

const esquemaEquipo = z.object({
  codigo_interno: z.string().min(1, { error: "El código interno es obligatorio." }).max(50),
  nombre: z.string().min(1, { error: "El nombre es obligatorio." }).max(200),
  estado_operativo: z.enum(ESTADOS_OPERATIVOS),
  categoria_id: z.string().optional(),
  area_id: z.string().optional(),
  marca: z.string().optional(),
  modelo: z.string().optional(),
  numero_serie: z.string().optional(),
  fabricante: z.string().optional(),
  proveedor: z.string().optional(),
  fecha_adquisicion: z.string().optional(),
  observaciones: z.string().optional(),
});

type FormularioEquipo = z.infer<typeof esquemaEquipo>;

export function EquipoFormPage() {
  const { id } = useParams<{ id: string }>();
  const modoEdicion = !!id;
  const navigate = useNavigate();

  const { data: categorias } = useCategorias();
  const { data: areas } = useAreas();
  const { data: equipoActual, isLoading: cargandoEquipo } = useEquipo(id);
  const crear = useCrearEquipo();
  const actualizar = useActualizarEquipo(id ?? "");

  // object_key que se envía al guardar: se inicializa con la foto actual y
  // solo cambia si el usuario sube una nueva — mismo criterio que el logo
  // institucional en LaboratorioSection (guardar sin tocar la foto no la borra).
  const [fotoObjectKey, setFotoObjectKey] = useState<string | null>(null);

  const inputManualRef = useRef<HTMLInputElement>(null);
  // Mismo criterio que la foto: se reenvía tal cual, nunca se omite.
  const [manualObjectKey, setManualObjectKey] = useState<string | null>(null);
  const [manualNombre, setManualNombre] = useState<string | null>(null);
  const [manualUrl, setManualUrl] = useState<string | null>(null);
  const [subiendoManual, setSubiendoManual] = useState(false);
  const [errorManual, setErrorManual] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormularioEquipo>({
    resolver: zodResolver(esquemaEquipo),
    defaultValues: { estado_operativo: "operativo" },
  });

  useEffect(() => {
    if (equipoActual) {
      reset({
        codigo_interno: equipoActual.codigo_interno,
        nombre: equipoActual.nombre,
        estado_operativo: equipoActual.estado_operativo,
        categoria_id: equipoActual.categoria_id ?? "",
        area_id: equipoActual.area_id ?? "",
        marca: equipoActual.marca ?? "",
        modelo: equipoActual.modelo ?? "",
        numero_serie: equipoActual.numero_serie ?? "",
        fabricante: equipoActual.fabricante ?? "",
        proveedor: equipoActual.proveedor ?? "",
        fecha_adquisicion: equipoActual.fecha_adquisicion ?? "",
        observaciones: equipoActual.observaciones ?? "",
      });
      setFotoObjectKey(equipoActual.foto_object_key);
      setManualObjectKey(equipoActual.manual_object_key);
      setManualUrl(equipoActual.manual_url);
      setManualNombre(null);
    }
  }, [equipoActual, reset]);

  async function subirFoto(archivo: File): Promise<string> {
    const { url_subida, object_key } = await solicitarUrlFoto(archivo.name, archivo.type, archivo.size);
    await fetch(url_subida, { method: "PUT", body: archivo, headers: { "Content-Type": archivo.type } });
    return object_key;
  }

  async function subirManual(archivo: File) {
    setErrorManual(null);
    setSubiendoManual(true);
    try {
      const { url_subida, object_key } = await solicitarUrlManual(archivo.name, archivo.type, archivo.size);
      await fetch(url_subida, { method: "PUT", body: archivo, headers: { "Content-Type": archivo.type } });
      setManualObjectKey(object_key);
      setManualNombre(archivo.name);
      setManualUrl(null);
    } catch (err) {
      setErrorManual(err instanceof ApiError ? err.message : "No se pudo subir el manual.");
    } finally {
      setSubiendoManual(false);
    }
  }

  async function onSubmit(datos: FormularioEquipo) {
    const payload = {
      ...datos,
      categoria_id: datos.categoria_id || null,
      area_id: datos.area_id || null,
      fecha_adquisicion: datos.fecha_adquisicion || null,
      // Siempre se reenvía tal cual (foto actual sin tocar, foto nueva
      // recién subida, o null si nunca hubo una) — omitirlo cuando no
      // cambió borraría la foto existente en cada edición no relacionada.
      foto_object_key: fotoObjectKey,
      manual_object_key: manualObjectKey,
    };
    try {
      const equipo = modoEdicion ? await actualizar.mutateAsync(payload) : await crear.mutateAsync(payload);
      navigate(`/equipos/${equipo.id}`);
    } catch (error) {
      if (error instanceof ApiError && error.codigo === "codigo_interno_duplicado") {
        setError("codigo_interno", { message: error.message });
      } else if (error instanceof ApiError) {
        setError("root", { message: error.message });
      }
    }
  }

  if (modoEdicion && cargandoEquipo) {
    return <div className="p-8 text-sm text-ink-soft">Cargando equipo…</div>;
  }

  return (
    <div className="mx-auto max-w-2xl p-6 sm:p-8">
      <Link
        to={modoEdicion ? `/equipos/${id}` : "/equipos"}
        className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-ink-soft hover:text-ink"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Volver
      </Link>

      <h1 className="font-display mb-6 text-2xl font-semibold text-ink">
        {modoEdicion ? "Editar equipo" : "Nuevo equipo"}
      </h1>

      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        <SubirFotoConPreview
          etiqueta="Fotografía"
          urlActual={equipoActual?.foto_url ?? null}
          onSubir={subirFoto}
          onSubidoExitosamente={setFotoObjectKey}
          iconoVacio={Camera}
          textoAyuda="JPG, PNG o WEBP. Máximo 5MB."
          altTexto="Fotografía del equipo"
          mensajeErrorDefecto="No se pudo subir la fotografía."
        />

        <div className="mb-4">
          <p className="mb-1.5 text-sm font-semibold text-ink-soft">Manual de usuario</p>
          <div className="flex items-center gap-3">
            <input
              ref={inputManualRef}
              type="file"
              accept="application/pdf"
              className="hidden"
              onChange={(e) => {
                const archivo = e.target.files?.[0];
                if (archivo) void subirManual(archivo);
              }}
            />
            <Button
              type="button"
              size="sm"
              variant="secondary"
              cargando={subiendoManual}
              onClick={() => inputManualRef.current?.click()}
            >
              <FileText className="h-4 w-4" aria-hidden="true" />
              {manualObjectKey ? "Reemplazar manual" : "Subir manual"}
            </Button>
            {manualNombre && <span className="truncate text-sm text-ink-soft">{manualNombre}</span>}
            {!manualNombre && manualUrl && (
              <a
                href={manualUrl}
                target="_blank"
                rel="noreferrer"
                className="text-sm font-medium text-primary-900 underline underline-offset-2"
              >
                Descargar manual actual
              </a>
            )}
          </div>
          <p className="mt-1.5 text-xs text-ink-soft">Solo PDF. Máximo 20MB.</p>
          {errorManual && (
            <p role="alert" aria-live="polite" className="mt-1 text-xs font-medium text-danger">
              {errorManual}
            </p>
          )}
        </div>

        <div className="grid grid-cols-1 gap-x-4 sm:grid-cols-2">
          <Input label="Código interno" error={errors.codigo_interno?.message} {...register("codigo_interno")} />
          <Select label="Estado operativo" error={errors.estado_operativo?.message} {...register("estado_operativo")}>
            {ESTADOS_OPERATIVOS.map((estado) => (
              <option key={estado} value={estado}>
                {ETIQUETAS_ESTADO[estado]}
              </option>
            ))}
          </Select>
        </div>

        <Input label="Nombre" error={errors.nombre?.message} {...register("nombre")} />

        <div className="grid grid-cols-1 gap-x-4 sm:grid-cols-2">
          <Select label="Categoría" error={errors.categoria_id?.message} {...register("categoria_id")}>
            <option value="">Sin especificar</option>
            {categorias?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
          </Select>
          <Select label="Área" error={errors.area_id?.message} {...register("area_id")}>
            <option value="">Sin especificar</option>
            {areas?.map((a) => (
              <option key={a.id} value={a.id}>
                {a.nombre}
              </option>
            ))}
          </Select>
        </div>

        <div className="grid grid-cols-1 gap-x-4 sm:grid-cols-2">
          <Input label="Marca" error={errors.marca?.message} {...register("marca")} />
          <Input label="Modelo" error={errors.modelo?.message} {...register("modelo")} />
        </div>

        <div className="grid grid-cols-1 gap-x-4 sm:grid-cols-2">
          <Input label="Número de serie" error={errors.numero_serie?.message} {...register("numero_serie")} />
          <Input label="Fabricante" error={errors.fabricante?.message} {...register("fabricante")} />
        </div>

        <div className="grid grid-cols-1 gap-x-4 sm:grid-cols-2">
          <Input label="Proveedor" error={errors.proveedor?.message} {...register("proveedor")} />
          <Input
            label="Fecha de adquisición"
            type="date"
            error={errors.fecha_adquisicion?.message}
            {...register("fecha_adquisicion")}
          />
        </div>

        <Textarea label="Observaciones" error={errors.observaciones?.message} {...register("observaciones")} />

        {errors.root?.message && (
          <p role="alert" aria-live="polite" className="mb-4 text-sm font-medium text-danger">
            {errors.root.message}
          </p>
        )}

        <div className="mt-2 flex gap-3">
          <Button type="submit" cargando={isSubmitting}>
            <Save className="h-4 w-4" aria-hidden="true" />
            {modoEdicion ? "Guardar cambios" : "Crear equipo"}
          </Button>
          <LinkButton to={modoEdicion ? `/equipos/${id}` : "/equipos"} variant="secondary">
            Cancelar
          </LinkButton>
        </div>
      </form>
    </div>
  );
}
