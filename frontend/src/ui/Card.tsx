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
        "rounded-sm border border-subtle bg-raised p-4 sm:p-5",
        className,
      )}
      {...rest}
    >
      {(title || actions) && (
        <header className="mb-3 flex items-center justify-between gap-3 border-b border-subtle pb-2">
          {title && (
            <h2 className="text-sm font-semibold tracking-wide text-primary">
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
