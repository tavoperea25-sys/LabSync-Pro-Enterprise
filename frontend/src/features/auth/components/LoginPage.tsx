import { zodResolver } from "@hookform/resolvers/zod";
import {
  Building2,
  Eye,
  EyeOff,
  FlaskConical,
  Lock,
  LogIn,
  ShieldCheck,
  User,
} from "lucide-react";
import { animate } from "motion";
import { motion, useReducedMotion, type Variants } from "motion/react";
import { useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { useLocation, useNavigate } from "react-router";
import { z } from "zod";

import { ApiError } from "@/lib/httpClient";
import { AmbientBackground } from "@/shared/components/AmbientBackground";
import { Button } from "@/shared/components/ui/button";
import { Checkbox } from "@/shared/components/ui/checkbox";
import { Input } from "@/shared/components/ui/input";

import { useAuth } from "../hooks/AuthProvider";

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

const cardVariants: Variants = {
  hidden: { opacity: 0, y: 20, scale: 0.985 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: 0.6, ease: EASE_OUT, staggerChildren: 0.05, delayChildren: 0.15 },
  },
};
const itemVariants: Variants = {
  hidden: { opacity: 0, y: 14 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: EASE_OUT } },
};

const esquemaLogin = z.object({
  laboratorio_slug: z.string().min(1, { error: "Ingresa el identificador de tu laboratorio." }),
  correo: z.email({ error: "Ingresa un correo válido." }),
  password: z.string().min(1, { error: "Por favor ingresa tu contraseña." }),
  recordarme: z.boolean(),
});

type FormularioLogin = z.infer<typeof esquemaLogin>;

interface Ripple {
  id: number;
  x: number;
  y: number;
  size: number;
}

export function LoginPage() {
  const { iniciarSesion } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const shouldReduceMotion = useReducedMotion();

  // RF-CFG-01: tras un cambio de contraseña propio, que revoca todas las
  // sesiones, se redirige aquí con un mensaje explicativo (ver PerfilSection).
  const mensajeInfo = (location.state as { mensaje?: string } | null)?.mensaje ?? null;

  const [mostrarPassword, setMostrarPassword] = useState(false);
  const [errorApi, setErrorApi] = useState<string | null>(null);
  const [ripples, setRipples] = useState<Ripple[]>([]);
  const [ayudaRecuperacion, setAyudaRecuperacion] = useState<string | null>(null);

  const eyeIconRef = useRef<SVGSVGElement>(null);
  const wrapRefs = {
    laboratorio_slug: useRef<HTMLDivElement>(null),
    correo: useRef<HTMLDivElement>(null),
    password: useRef<HTMLDivElement>(null),
  };
  const iconRefs = {
    laboratorio_slug: useRef<HTMLSpanElement>(null),
    correo: useRef<HTMLSpanElement>(null),
    password: useRef<HTMLSpanElement>(null),
  };

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormularioLogin>({
    resolver: zodResolver(esquemaLogin),
    defaultValues: { recordarme: false },
  });

  function toggleMostrarPassword() {
    setMostrarPassword((v) => !v);
    if (!shouldReduceMotion && eyeIconRef.current) {
      animate(eyeIconRef.current, { scale: [0.7, 1] }, { duration: 0.28, ease: EASE_OUT });
    }
  }

  function onFocusCampo(campo: keyof typeof iconRefs) {
    const icon = iconRefs[campo].current;
    if (!shouldReduceMotion && icon) {
      animate(icon, { scale: [1, 1.15, 1] }, { duration: 0.3, ease: EASE_OUT });
    }
  }

  function shakeCampo(campo: keyof typeof wrapRefs) {
    const wrap = wrapRefs[campo].current;
    if (!shouldReduceMotion && wrap) {
      animate(wrap, { x: [0, -6, 6, -4, 4, 0] }, { duration: 0.4, ease: "easeInOut" });
    }
  }

  function crearRipple(evt: React.MouseEvent<HTMLButtonElement>) {
    if (shouldReduceMotion) return;
    const btn = evt.currentTarget;
    const rect = btn.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height) * 1.6;
    const nuevo: Ripple = {
      id: Date.now(),
      x: evt.clientX - rect.left - size / 2,
      y: evt.clientY - rect.top - size / 2,
      size,
    };
    setRipples((prev) => [...prev, nuevo]);
  }

  async function onSubmit(datos: FormularioLogin) {
    setErrorApi(null);
    try {
      await iniciarSesion(datos);
      navigate("/dashboard");
    } catch (error) {
      if (error instanceof ApiError) {
        setErrorApi(error.message);
        (["laboratorio_slug", "correo", "password"] as const).forEach((campo) => {
          if (errors[campo]) shakeCampo(campo);
        });
      } else {
        setErrorApi("No se pudo conectar con el servidor. Intenta de nuevo.");
      }
    }
  }

  return (
    <div className="tema-fijo-claro relative flex min-h-dvh items-center justify-center overflow-x-hidden bg-gradient-to-br from-white via-[#F6FBF8] to-[#EAF7EF] p-6">
      <AmbientBackground />

      <motion.main
        variants={cardVariants}
        initial={shouldReduceMotion ? false : "hidden"}
        animate="visible"
        className="relative z-10 flex w-full max-w-[1000px] overflow-hidden rounded-xl shadow-ambient md:min-h-[620px]"
      >
        {/* PANEL IZQUIERDO — institucional */}
        <section
          aria-label="Información institucional"
          className="relative hidden w-[340px] flex-shrink-0 flex-col justify-between overflow-hidden bg-gradient-to-br from-primary-900 to-[#0B3B24] p-8 pb-10 md:flex"
        >
          <div
            className="pointer-events-none absolute inset-0"
            style={{
              background:
                "radial-gradient(circle at 15% 10%, rgba(143,217,174,.35) 0%, transparent 45%), radial-gradient(circle at 90% 85%, rgba(27,122,74,.55) 0%, transparent 55%)",
            }}
          />

          <motion.div
            variants={itemVariants}
            className="relative z-10 inline-flex w-fit items-center gap-1.5 self-start rounded-full border border-white/20 bg-white/10 py-1.5 pl-2.5 pr-3.5 text-xs font-medium tracking-wide text-white/90 backdrop-blur-[10px]"
          >
            <ShieldCheck className="h-3.5 w-3.5 text-primary-light" aria-hidden="true" />
            Acceso institucional
          </motion.div>

          <div className="relative z-10 flex flex-col gap-10">
            <div className="text-center">
              <motion.div
                variants={itemVariants}
                className="mx-auto mb-4 flex h-[92px] w-[92px] items-center justify-center rounded-full border-[1.5px] border-white/30 bg-white/95 p-1.5 shadow-[0_10px_30px_rgba(0,0,0,.28)]"
              >
                <FlaskConical className="h-9 w-9 text-primary-900" strokeWidth={1.75} aria-hidden="true" />
              </motion.div>
              <motion.p
                variants={itemVariants}
                className="font-brand mx-auto max-w-[230px] text-lg italic leading-relaxed text-white/95"
              >
                Gestión inteligente para laboratorios modernos
              </motion.p>
            </div>

            <motion.ul variants={itemVariants} className="flex flex-col gap-3">
              {[
                "Trazabilidad completa de equipos",
                "Gestión documental centralizada",
                "Cumplimiento normativo garantizado",
              ].map((texto) => (
                <li key={texto} className="flex items-start gap-2.5 text-[13.5px] leading-snug text-white/85">
                  <ShieldCheck className="mt-0.5 h-[17px] w-[17px] flex-shrink-0 text-primary-light" aria-hidden="true" />
                  {texto}
                </li>
              ))}
            </motion.ul>
          </div>
        </section>

        {/* PANEL DERECHO — formulario (glass) */}
        <section
          aria-label="Formulario de inicio de sesión"
          className="flex flex-1 flex-col justify-center bg-white/[.78] px-6 py-10 backdrop-blur-[22px] backdrop-saturate-[1.6] sm:px-10 md:py-12"
        >
          <motion.div variants={itemVariants} className="mb-7 text-center">
            <div className="mx-auto mb-3 flex h-[54px] w-[54px] items-center justify-center rounded-full bg-primary-tint">
              <ShieldCheck className="h-[27px] w-[27px] text-primary-900" strokeWidth={1.8} aria-hidden="true" />
            </div>
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-[3px] text-primary-600">
              Portal de acceso
            </p>
            <h1 className="font-display mb-1.5 text-[25px] font-semibold leading-tight text-ink">
              Inicia sesión
            </h1>
            <p className="text-[13.5px] leading-relaxed text-ink-soft">
              Ingresa tus credenciales institucionales para continuar
            </p>
          </motion.div>

          <motion.div variants={itemVariants} className="mb-6 flex items-center gap-2.5">
            <div className="h-px flex-1 bg-border" />
            <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-primary-tint">
              <FlaskConical className="h-[17px] w-[17px] text-primary-900" aria-hidden="true" />
            </div>
            <div className="h-px flex-1 bg-border" />
          </motion.div>

          <form onSubmit={handleSubmit(onSubmit)} noValidate>
            <motion.div variants={itemVariants} ref={wrapRefs.laboratorio_slug}>
              <Input
                label="Laboratorio"
                placeholder="ej. demo"
                autoComplete="organization"
                error={errors.laboratorio_slug?.message}
                icono={
                  <span ref={iconRefs.laboratorio_slug} className="inline-flex">
                    <Building2 className="h-[17px] w-[17px]" aria-hidden="true" />
                  </span>
                }
                onFocus={() => onFocusCampo("laboratorio_slug")}
                {...register("laboratorio_slug")}
              />
            </motion.div>

            <motion.div variants={itemVariants} ref={wrapRefs.correo}>
              <Input
                label="Correo"
                type="email"
                placeholder="usuario@laboratorio.com"
                autoComplete="username"
                error={errors.correo?.message}
                icono={
                  <span ref={iconRefs.correo} className="inline-flex">
                    <User className="h-[17px] w-[17px]" aria-hidden="true" />
                  </span>
                }
                onFocus={() => onFocusCampo("correo")}
                {...register("correo")}
              />
            </motion.div>

            <motion.div variants={itemVariants} ref={wrapRefs.password}>
              <Input
                label="Contraseña"
                type={mostrarPassword ? "text" : "password"}
                placeholder="Ingresa tu contraseña"
                autoComplete="current-password"
                error={errors.password?.message}
                icono={
                  <span ref={iconRefs.password} className="inline-flex">
                    <Lock className="h-[17px] w-[17px]" aria-hidden="true" />
                  </span>
                }
                onFocus={() => onFocusCampo("password")}
                accion={
                  <button
                    type="button"
                    onClick={toggleMostrarPassword}
                    aria-label={mostrarPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
                    aria-pressed={mostrarPassword}
                    className="flex h-[38px] w-[38px] items-center justify-center rounded-lg text-[#8ea198] transition-colors duration-fast hover:bg-primary-tint hover:text-primary-900"
                  >
                    {mostrarPassword ? (
                      <EyeOff ref={eyeIconRef} className="h-[18px] w-[18px]" aria-hidden="true" />
                    ) : (
                      <Eye ref={eyeIconRef} className="h-[18px] w-[18px]" aria-hidden="true" />
                    )}
                  </button>
                }
                {...register("password")}
              />
            </motion.div>

            <motion.div variants={itemVariants} className="mb-5 mt-2 flex flex-wrap items-center justify-between gap-2">
              <Checkbox label="Recordarme" {...register("recordarme")} />
              <button
                type="button"
                onClick={() =>
                  setAyudaRecuperacion("Contacta al administrador del sistema para restablecer tu contraseña.")
                }
                className="-my-1.5 -mx-1 rounded-md px-1 py-1.5 text-[13px] font-semibold text-primary-600 transition-colors duration-fast hover:text-primary-900 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-900"
              >
                ¿Olvidaste tu contraseña?
              </button>
            </motion.div>

            {ayudaRecuperacion && (
              <p aria-live="polite" className="-mt-3 mb-4 text-xs text-ink-soft">
                {ayudaRecuperacion}
              </p>
            )}

            {mensajeInfo && !errorApi && (
              <p role="status" aria-live="polite" className="mb-4 text-sm font-medium text-primary-600">
                {mensajeInfo}
              </p>
            )}

            {errorApi && (
              <p role="alert" aria-live="polite" className="mb-4 text-sm font-medium text-danger">
                {errorApi}
              </p>
            )}

            <motion.div variants={itemVariants}>
              <Button
                type="submit"
                variant="primary"
                size="lg"
                cargando={isSubmitting}
                onMouseDown={crearRipple}
                whileHover={shouldReduceMotion ? undefined : { scale: 1.015, y: -2 }}
                whileTap={shouldReduceMotion ? undefined : { scale: 0.98 }}
                transition={{ duration: 0.25, ease: "easeOut" }}
                className="relative w-full overflow-hidden bg-gradient-to-br from-primary-900 to-primary-600 shadow-btn hover:shadow-btn-hover"
              >
                <LogIn className="h-4 w-4" aria-hidden="true" />
                Iniciar sesión
                {ripples.map((r) => (
                  <span
                    key={r.id}
                    className="animate-ripple pointer-events-none absolute rounded-full bg-white/50"
                    style={{ width: r.size, height: r.size, left: r.x, top: r.y, transform: "scale(0)" }}
                    onAnimationEnd={() => setRipples((prev) => prev.filter((x) => x.id !== r.id))}
                  />
                ))}
              </Button>
            </motion.div>
          </form>

          <motion.div variants={itemVariants} className="mt-5 text-center">
            <div className="mb-1.5 flex items-center justify-center gap-1.5 text-xs text-ink-soft">
              <Lock className="h-[13px] w-[13px] text-primary-900" aria-hidden="true" />
              Acceso seguro
            </div>
            <p className="text-[11px] leading-relaxed text-ink-soft">
              Sistema confidencial de gestión de laboratorios clínicos
              <br />© 2026 LabSync Pro Enterprise. Todos los derechos reservados.
            </p>
          </motion.div>

          <motion.div
            variants={itemVariants}
            className="mt-4 flex items-start gap-3 rounded-md bg-primary-tint p-3.5"
          >
            <div className="flex h-[34px] w-[34px] flex-shrink-0 items-center justify-center rounded-full bg-primary-900/10">
              <ShieldCheck className="h-4 w-4 text-primary-900" aria-hidden="true" />
            </div>
            <div>
              <p className="mb-0.5 text-[12.5px] font-bold text-primary-900">Acceso restringido</p>
              <p className="text-[11.5px] leading-relaxed text-[#3c6b4c]">
                Este sistema es de uso exclusivo para personal autorizado.
                <br />
                Todas las actividades son monitoreadas y registradas.
              </p>
            </div>
          </motion.div>
        </section>
      </motion.main>
    </div>
  );
}
