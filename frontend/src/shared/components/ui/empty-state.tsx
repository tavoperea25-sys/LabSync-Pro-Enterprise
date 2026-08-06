import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

/** Ver docs/12-component-library.md — EmptyState. */
export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 px-6 py-16 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary-tint">
        <Icon className="h-6 w-6 text-primary-900" aria-hidden="true" />
      </div>
      <h2 className="font-display text-base font-semibold text-ink">{title}</h2>
      {description && <p className="max-w-sm text-sm text-ink-soft">{description}</p>}
      {action}
    </div>
  );
}
