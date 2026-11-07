import "@testing-library/jest-dom/vitest";
import { z } from "zod";

// Mismo locale que src/main.tsx — los tests no cargan el entrypoint real,
// así que sin esto los mensajes por defecto de zod (p. ej. .max() sin
// mensaje explícito) saldrían en inglés en la suite.
z.config(z.locales.es());

// jsdom no implementa matchMedia — lo necesitan tanto la detección de
// prefers-color-scheme (ThemeProvider) como useReducedMotion (motion/react).
if (!window.matchMedia) {
  window.matchMedia = (query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }) as MediaQueryList;
}
