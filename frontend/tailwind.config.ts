import tailwindcssAnimate from "tailwindcss-animate";
import type { Config } from "tailwindcss";

// Tokens espejo de docs/11-design-system.md — única fuente de verdad de
// color/tipografía/espaciado/radios para toda la plataforma.
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          900: "#0F5132",
          600: "#198754",
          // "light"/"tint" heredados del login original (docs/11-design-system.md
          // sección 0): 100 es el badge/superficie de apoyo del design system;
          // light/tint cubren acentos sobre fondo oscuro y tintes de ícono que
          // #100 por sí solo deja planos.
          light: "#8FD9AE",
          tint: "#EAF7EF",
          100: "#D1E7DD",
        },
        surface: "var(--surface)",
        "surface-alt": "var(--surface-alt)",
        border: "var(--border)",
        ink: {
          DEFAULT: "var(--text-primary)",
          soft: "var(--text-secondary)",
        },
        success: "#16A34A",
        warning: "#F59E0B",
        danger: "#DC2626",
        info: "#2563EB",
      },
      fontFamily: {
        display: ["'Plus Jakarta Sans'", "sans-serif"],
        body: ["'Inter'", "sans-serif"],
        // Solo para el panel institucional del login (docs/11-design-system.md
        // sección 0) — no se propaga al resto de la plataforma.
        brand: ["'Fraunces'", "Georgia", "serif"],
      },
      borderRadius: {
        sm: "10px",
        md: "14px",
        lg: "20px",
        xl: "28px",
      },
      transitionDuration: {
        fast: "150ms",
        base: "220ms",
      },
      boxShadow: {
        ambient: "0 40px 100px rgba(15,81,50,.18), 0 10px 30px rgba(15,81,50,.10)",
        btn: "0 4px 18px rgba(15,81,50,.30)",
        "btn-hover": "0 12px 30px rgba(15,81,50,.36)",
      },
      transitionTimingFunction: {
        "brand-out": "cubic-bezier(.16,1,.3,1)",
      },
    },
  },
  plugins: [tailwindcssAnimate],
} satisfies Config;
