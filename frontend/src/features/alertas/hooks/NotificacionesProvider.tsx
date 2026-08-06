import { useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Bell, X } from "lucide-react";
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";

import { useAuth } from "@/features/auth/hooks/AuthProvider";
import { getAccessToken } from "@/lib/httpClient";

import type { EventoNotificacion } from "../types";

interface NotificacionesContextValue {
  /** false => los hooks de lectura deben caer a polling (fallback, RF-ALT-06). */
  conectado: boolean;
}

const NotificacionesContext = createContext<NotificacionesContextValue>({ conectado: false });

// eslint-disable-next-line react-refresh/only-export-components
export function useConectadoWebSocket(): boolean {
  return useContext(NotificacionesContext).conectado;
}

interface Toast {
  id: string;
  evento: EventoNotificacion;
}

const DURACION_TOAST_MS = 6000;
const REINTENTO_INICIAL_MS = 3000;
const REINTENTO_MAXIMO_MS = 30000;

/** Puente WebSocket -> UI: mantiene la conexión a `/ws/v1/notificaciones`
 * (con reconexión con backoff), invalida las queries de alertas cuando
 * llega un evento y muestra un toast — con fallback a polling (ver
 * `useConectadoWebSocket`, consumido por los hooks de `useAlertas.ts`) si
 * el socket no logra conectar. Se monta una sola vez en `AppShell`, no por
 * página, para no reconectar al navegar. */
export function NotificacionesProvider({ children }: { children: ReactNode }) {
  const { usuario } = useAuth();
  const queryClient = useQueryClient();
  const [conectado, setConectado] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const socketRef = useRef<WebSocket | null>(null);
  const intentoRef = useRef(0);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const activoRef = useRef(false);

  useEffect(() => {
    if (!usuario) return;
    activoRef.current = true;

    function conectar() {
      const token = getAccessToken();
      if (!token || !activoRef.current) return;

      const protocolo = window.location.protocol === "https:" ? "wss:" : "ws:";
      // Fase 2/M5 — el token viaja como subprotocolo ofrecido en el
      // handshake (`Sec-WebSocket-Protocol`), no en la URL: así no queda en
      // logs de acceso ni en los de un futuro reverse proxy. El backend
      // espera exactamente este marcador seguido del token
      // (app/modules/alertas/presentation/websocket_router.py).
      const socket = new WebSocket(`${protocolo}//${window.location.host}/ws/v1/notificaciones`, [
        "access_token",
        token,
      ]);
      socketRef.current = socket;

      socket.onopen = () => {
        intentoRef.current = 0;
        setConectado(true);
      };

      socket.onmessage = (evento) => {
        try {
          const datos = JSON.parse(evento.data) as EventoNotificacion;
          // Mismo canal WS para dos orígenes de evento (ver EventoNotificacion) —
          // cada uno invalida solo las queries que le corresponden.
          if (datos.evento === "reporte.listo") {
            queryClient.invalidateQueries({ queryKey: ["reportes"] });
          } else {
            queryClient.invalidateQueries({ queryKey: ["alertas"] });
          }
          setToasts((actuales) => [...actuales, { id: crypto.randomUUID(), evento: datos }]);
        } catch {
          // Payload inesperado — se ignora, no rompe la conexión.
        }
      };

      socket.onclose = () => {
        setConectado(false);
        socketRef.current = null;
        if (!activoRef.current) return;
        const espera = Math.min(REINTENTO_INICIAL_MS * 2 ** intentoRef.current, REINTENTO_MAXIMO_MS);
        intentoRef.current += 1;
        timeoutRef.current = setTimeout(conectar, espera);
      };

      socket.onerror = () => socket.close();
    }

    conectar();

    return () => {
      activoRef.current = false;
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      socketRef.current?.close();
    };
  }, [usuario, queryClient]);

  function descartarToast(id: string) {
    setToasts((actuales) => actuales.filter((t) => t.id !== id));
  }

  return (
    <NotificacionesContext.Provider value={{ conectado }}>
      {children}
      <ToastStack toasts={toasts} onDescartar={descartarToast} />
    </NotificacionesContext.Provider>
  );
}

function ToastStack({ toasts, onDescartar }: { toasts: Toast[]; onDescartar: (id: string) => void }) {
  return (
    <div
      aria-live="polite"
      className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-full max-w-sm flex-col gap-2"
    >
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDescartar={() => onDescartar(toast.id)} />
      ))}
    </div>
  );
}

function ToastItem({ toast, onDescartar }: { toast: Toast; onDescartar: () => void }) {
  useEffect(() => {
    const id = setTimeout(onDescartar, DURACION_TOAST_MS);
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const critica = toast.evento.tipo === "critica";

  return (
    <div
      role="status"
      className="pointer-events-auto flex items-start gap-2.5 rounded-md border border-border bg-surface p-3 shadow-ambient"
    >
      <div
        className={`mt-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full ${
          critica ? "bg-[#FEE2E2] text-[#991B1B]" : "bg-[#FEF3C7] text-[#92400E]"
        }`}
      >
        {critica ? (
          <AlertTriangle className="h-4 w-4" aria-hidden="true" />
        ) : (
          <Bell className="h-4 w-4" aria-hidden="true" />
        )}
      </div>
      <p className="flex-1 text-sm text-ink">{toast.evento.mensaje}</p>
      <button
        type="button"
        aria-label="Descartar notificación"
        onClick={onDescartar}
        className="text-ink-soft hover:text-ink"
      >
        <X className="h-4 w-4" aria-hidden="true" />
      </button>
    </div>
  );
}
