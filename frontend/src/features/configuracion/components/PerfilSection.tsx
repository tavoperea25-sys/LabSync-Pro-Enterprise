import { Camera, KeyRound, User } from "lucide-react";
import { useState } from "react";

import { CambiarPasswordForm } from "@/features/auth/components/CambiarPasswordForm";
import { useAuth } from "@/features/auth/hooks/AuthProvider";
import { ApiError } from "@/lib/httpClient";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { SubirFotoConPreview } from "@/shared/components/ui/subir-foto-con-preview";

import { solicitarUrlFotoPerfil } from "../api/configuracionApi";
import { useActualizarPerfilPropio } from "../hooks/useConfiguracion";

export function PerfilSection() {
  const { usuario, actualizarUsuario } = useAuth();
  const actualizarPerfil = useActualizarPerfilPropio();

  const [nombreCompleto, setNombreCompleto] = useState(usuario?.nombre_completo ?? "");
  const [correo, setCorreo] = useState(usuario?.correo ?? "");
  // object_key que se reenvía al guardar: se inicializa con la foto actual
  // y solo cambia si el usuario sube una nueva — mismo criterio que el logo
  // institucional (LaboratorioSection). Reenviarlo tal cual (no omitirlo)
  // es lo que evita que guardar nombre/correo borre la foto por accidente.
  const [fotoObjectKey, setFotoObjectKey] = useState<string | null>(usuario?.foto_object_key ?? null);
  const [errorPerfil, setErrorPerfil] = useState<string | null>(null);
  const [exitoPerfil, setExitoPerfil] = useState(false);

  async function subirFoto(archivo: File): Promise<string> {
    const { url_subida, object_key } = await solicitarUrlFotoPerfil(archivo.name, archivo.type, archivo.size);
    await fetch(url_subida, { method: "PUT", body: archivo, headers: { "Content-Type": archivo.type } });
    return object_key;
  }

  async function guardarPerfil() {
    setExitoPerfil(false);
    if (!nombreCompleto.trim() || !correo.trim()) {
      setErrorPerfil("Nombre y correo son obligatorios.");
      return;
    }
    setErrorPerfil(null);
    try {
      const actualizado = await actualizarPerfil.mutateAsync({
        nombre_completo: nombreCompleto.trim(),
        correo: correo.trim(),
        foto_object_key: fotoObjectKey,
      });
      actualizarUsuario({
        id: actualizado.id,
        nombre_completo: actualizado.nombre_completo,
        correo: actualizado.correo,
        roles: actualizado.roles,
        debe_cambiar_password: actualizado.debe_cambiar_password,
        foto_url: actualizado.foto_url,
        foto_object_key: actualizado.foto_object_key,
      });
      setExitoPerfil(true);
    } catch (err) {
      setErrorPerfil(err instanceof ApiError ? err.message : "No se pudo actualizar el perfil.");
    }
  }

  return (
    <div className="max-w-xl space-y-8">
      <section>
        <h2 className="mb-1 flex items-center gap-2 font-display text-base font-semibold text-ink">
          <User className="h-4 w-4 text-primary-900" aria-hidden="true" />
          Mi perfil
        </h2>
        <p className="mb-4 text-sm text-ink-soft">Tu nombre y correo, visibles para el resto del equipo.</p>

        <SubirFotoConPreview
          etiqueta="Fotografía"
          urlActual={usuario?.foto_url ?? null}
          onSubir={subirFoto}
          onSubidoExitosamente={setFotoObjectKey}
          iconoVacio={User}
          iconoBoton={Camera}
          textoAyuda="JPG, PNG o WEBP. Máximo 2MB."
          altTexto="Tu fotografía de perfil"
          forma="circulo"
          tamano="sm"
          mensajeErrorDefecto="No se pudo subir la fotografía."
        />

        <Input label="Nombre completo" value={nombreCompleto} onChange={(e) => setNombreCompleto(e.target.value)} />
        <Input label="Correo" type="email" value={correo} onChange={(e) => setCorreo(e.target.value)} />
        {errorPerfil && (
          <p role="alert" aria-live="polite" className="mb-3 text-sm font-medium text-danger">
            {errorPerfil}
          </p>
        )}
        {exitoPerfil && (
          <p role="status" aria-live="polite" className="mb-3 text-sm font-medium text-[#065F46]">
            Perfil actualizado.
          </p>
        )}
        <Button size="sm" cargando={actualizarPerfil.isPending} onClick={guardarPerfil}>
          Guardar cambios
        </Button>
      </section>

      <section className="border-t border-border pt-6">
        <h2 className="mb-1 flex items-center gap-2 font-display text-base font-semibold text-ink">
          <KeyRound className="h-4 w-4 text-primary-900" aria-hidden="true" />
          Cambiar contraseña
        </h2>
        <p className="mb-4 text-sm text-ink-soft">
          Al cambiarla, se cierran todas tus sesiones activas y deberás iniciar sesión de nuevo.
        </p>
        <CambiarPasswordForm />
      </section>
    </div>
  );
}
