import { Moon, Sun } from "lucide-react";

import { useTheme } from "@/shared/hooks/ThemeProvider";

export function ThemeToggle() {
  const { tema, alternarTema } = useTheme();
  const esOscuro = tema === "dark";

  return (
    <button
      type="button"
      onClick={alternarTema}
      aria-label={esOscuro ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
      className="flex h-9 w-9 items-center justify-center rounded-md text-ink-soft transition-colors duration-fast hover:bg-surface-alt hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-900"
    >
      {esOscuro ? <Sun className="h-[18px] w-[18px]" aria-hidden="true" /> : <Moon className="h-[18px] w-[18px]" aria-hidden="true" />}
    </button>
  );
}
