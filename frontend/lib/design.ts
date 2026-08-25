/** Shared design utilities for consistent UI across features. */

export const formControlClass =
  "input-3d flex h-11 w-full rounded-xl px-3.5 py-2 text-sm focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50";

export const textareaClass =
  "input-3d flex min-h-[140px] w-full rounded-xl px-3.5 py-2 text-sm focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50";

export function scoreTextClass(score: number): string {
  if (score >= 80) return "text-success";
  if (score >= 60) return "text-warning";
  return "text-destructive";
}

export function scoreStrokeHex(score: number): string {
  if (score >= 80) return "hsl(152 35% 36%)";
  if (score >= 60) return "hsl(32 70% 42%)";
  return "hsl(0 62% 48%)";
}
