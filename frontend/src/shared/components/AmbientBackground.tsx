/**
 * Fondo ambiental de las pantallas de autenticación: 3 blobs difuminados
 * en flotación lenta + un patrón de líneas moleculares, portado del login
 * original ya auditado en accesibilidad (marcado `aria-hidden`, capa
 * `pointer-events-none`, animaciones puramente decorativas neutralizadas
 * por `prefers-reduced-motion` a nivel de CSS — ver globals.css).
 */
export function AmbientBackground() {
  return (
    <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden" aria-hidden="true">
      <div
        className="animate-float-a absolute -left-[120px] -top-[140px] h-[520px] w-[520px] rounded-full opacity-45 blur-[90px]"
        style={{ background: "radial-gradient(circle, #0F5132 0%, transparent 70%)" }}
      />
      <div
        className="animate-float-b absolute -right-[100px] -bottom-[160px] h-[460px] w-[460px] rounded-full opacity-[.38] blur-[90px]"
        style={{ background: "radial-gradient(circle, #8FD9AE 0%, transparent 70%)" }}
      />
      <div
        className="animate-float-c absolute right-[8%] top-[40%] h-[380px] w-[380px] rounded-full opacity-[.28] blur-[90px]"
        style={{ background: "radial-gradient(circle, #198754 0%, transparent 70%)" }}
      />
      <svg
        className="absolute right-[-40px] top-1/2 h-screen w-[460px] -translate-y-1/2 opacity-50"
        viewBox="0 0 500 800"
        preserveAspectRatio="xMaxYMid meet"
      >
        <g opacity="0.2" stroke="#0F5132" strokeWidth="1.3">
          <line x1="60" y1="80" x2="170" y2="150" />
          <line x1="170" y1="150" x2="310" y2="100" />
          <line x1="310" y1="100" x2="440" y2="170" />
          <line x1="440" y1="170" x2="390" y2="300" />
          <line x1="390" y1="300" x2="470" y2="400" />
          <line x1="470" y1="400" x2="350" y2="460" />
          <line x1="350" y1="460" x2="450" y2="560" />
          <line x1="450" y1="560" x2="370" y2="660" />
          <line x1="170" y1="150" x2="270" y2="260" />
          <line x1="270" y1="260" x2="390" y2="300" />
          <line x1="270" y1="260" x2="210" y2="380" />
          <line x1="210" y1="380" x2="350" y2="460" />
          <line x1="310" y1="100" x2="270" y2="260" />
          <line x1="370" y1="660" x2="460" y2="730" />
          <line x1="210" y1="380" x2="120" y2="480" />
        </g>
        <g opacity="0.32" fill="#1B7A4A">
          <circle cx="60" cy="80" r="5" />
          <circle cx="170" cy="150" r="5" />
          <circle cx="310" cy="100" r="5" />
          <circle cx="440" cy="170" r="5" />
          <circle cx="390" cy="300" r="5" />
          <circle cx="470" cy="400" r="5" />
          <circle cx="350" cy="460" r="5" />
          <circle cx="450" cy="560" r="5" />
          <circle cx="370" cy="660" r="5" />
          <circle cx="270" cy="260" r="5" />
          <circle cx="210" cy="380" r="5" />
          <circle cx="460" cy="730" r="5" />
          <circle cx="120" cy="480" r="5" />
        </g>
      </svg>
    </div>
  );
}
