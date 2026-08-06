import type { VariantProps } from "class-variance-authority";
import { Link, type LinkProps } from "react-router-dom";

import { cn } from "@/shared/lib/cn";

import { buttonVariants } from "./button";

/** `<Link>` con la apariencia de Button — evita anidar <button> dentro de
 * <a> (HTML inválido) cuando la acción es navegación, no un evento local. */
export interface LinkButtonProps extends LinkProps, VariantProps<typeof buttonVariants> {
  className?: string;
}

export function LinkButton({ className, variant, size, ...props }: LinkButtonProps) {
  return <Link className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}
