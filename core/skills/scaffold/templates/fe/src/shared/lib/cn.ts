import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/** Merge class names, with later Tailwind utilities winning over earlier ones.
 *
 * `clsx` handles the conditionals; `twMerge` resolves the conflicts `clsx`
 * cannot see — `cn('p-2', 'p-4')` is `p-4`, not both. Every shadcn component
 * imports this (see the `utils` alias in components.json). */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
