import "@testing-library/jest-dom/vitest";

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
