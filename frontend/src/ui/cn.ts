import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** clsx + tailwind-merge, so a later conflicting utility (e.g. a caller's
 * `border-dashed` overriding a component's default `border-subtle`) wins
 * deterministically instead of depending on Tailwind's generated CSS order. */
export const cn = (...classes: ClassValue[]) => twMerge(clsx(classes));
