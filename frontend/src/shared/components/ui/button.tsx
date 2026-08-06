import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";
import { motion, type HTMLMotionProps } from "motion/react";
import { forwardRef, type ReactNode } from "react";

import { cn } from "@/shared/lib/cn";

/** Ver docs/12-component-library.md — componente Button. Construido sobre
 * `motion.button` para que cualquier consumidor pueda usar `whileHover`/
 * `whileTap` sin envolver el botón en un wrapper adicional; motion respeta
 * `prefers-reduced-motion` automáticamente vía `<MotionConfig>` en la raíz. */
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-sm text-sm font-semibold transition-colors " +
    "duration-fast focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 " +
    "focus-visible:outline-primary-900 disabled:cursor-not-allowed disabled:opacity-50",
  {
    variants: {
      variant: {
        primary: "bg-primary-900 text-white hover:bg-primary-600",
        secondary: "border border-border bg-transparent text-ink hover:bg-surface-alt",
        destructive: "bg-danger text-white hover:brightness-110",
        ghost: "bg-transparent text-ink hover:bg-surface-alt",
      },
      size: {
        sm: "h-9 px-3",
        md: "h-11 px-4",
        lg: "h-12 px-6 text-base",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

// Se reexporta para <LinkButton> (misma apariencia visual sobre <a>, no <button>).
// eslint-disable-next-line react-refresh/only-export-components
export { buttonVariants };

export interface ButtonProps extends HTMLMotionProps<"button">, VariantProps<typeof buttonVariants> {
  cargando?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, cargando, disabled, children, ...props }, ref) => (
    <motion.button
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={disabled || cargando}
      aria-busy={cargando}
      {...props}
    >
      {cargando && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
      {children as ReactNode}
    </motion.button>
  ),
);
Button.displayName = "Button";
