import { cn } from "./cn";

const base =
  "w-full rounded-sm border border-navy-600 bg-navy-900 px-3 py-2 text-sm outline-none focus:border-indigo-300 disabled:opacity-50";

/** Shared styling for text inputs / selects / textareas. */
export const textInputClass = (className?: string) => cn(base, className);
