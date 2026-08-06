import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";

import { cn } from "@/shared/lib/cn";

/** Ver docs/12-component-library.md — Badge. Siempre texto además del
 * color (nunca solo un punto de color) — ver docs/11-design-system.md. */
const badgeVariants = cva("inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium", {
  variants: {
    variant: {
      neutral: "bg-surface-alt text-ink-soft",
      success: "bg-[#D1FAE5] text-[#065F46]",
      warning: "bg-[#FEF3C7] text-[#92400E]",
      danger: "bg-[#FEE2E2] text-[#991B1B]",
      info: "bg-[#DBEAFE] text-[#1E40AF]",
    },
  },
  defaultVariants: { variant: "neutral" },
});

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
