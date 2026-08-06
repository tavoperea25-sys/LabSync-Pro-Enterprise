import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

type Tema = "light" | "dark";
const CLAVE_STORAGE = "labsync-tema";

interface ThemeContextValue {
  tema: Tema;
  alternarTema: () => void;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

function resolverTemaInicial(): Tema {
  const guardado = localStorage.getItem(CLAVE_STORAGE);
  if (guardado === "light" || guardado === "dark") return guardado;
  // RF-CFG-02 / docs/11-design-system.md: si el usuario no eligió
  // explícitamente, se respeta prefers-color-scheme como valor inicial.
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [tema, setTema] = useState<Tema>(resolverTemaInicial);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", tema === "dark");
    localStorage.setItem(CLAVE_STORAGE, tema);
  }, [tema]);

  function alternarTema() {
    setTema((t) => (t === "dark" ? "light" : "dark"));
  }

  return <ThemeContext.Provider value={{ tema, alternarTema }}>{children}</ThemeContext.Provider>;
}

// Patrón estándar de provider+hook co-ubicados; separarlos en dos archivos
// no aporta claridad aquí, solo indirección.
// eslint-disable-next-line react-refresh/only-export-components
export function useTheme(): ThemeContextValue {
  const contexto = useContext(ThemeContext);
  if (!contexto) throw new Error("useTheme debe usarse dentro de <ThemeProvider>.");
  return contexto;
}
