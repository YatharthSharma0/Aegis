import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "./cn";

interface Props extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  title?: ReactNode;
  actions?: ReactNode;
}

export function Card({ title, actions, className, children, ...rest }: Props) {
  return (
    <section
      className={cn(
        "rounded border border-navy-700 bg-navy-800/60 p-4 sm:p-5",
        className,
      )}
      {...rest}
    >
      {(title || actions) && (
        <header className="mb-3 flex items-center justify-between gap-3">
          {title && (
            <h2 className="text-sm font-semibold tracking-wide text-slate-200">
              {title}
            </h2>
          )}
          {actions}
        </header>
      )}
      {children}
    </section>
  );
}
