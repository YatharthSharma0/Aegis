import { cn } from "./cn";

const base =
  "w-full rounded-sm border border-subtle bg-base px-3 py-2 text-sm text-primary outline-none transition-colors duration-fast focus:border-strong disabled:opacity-[.42]";

/** Shared styling for text inputs / selects / textareas. */
export const textInputClass = (className?: string) => cn(base, className);
