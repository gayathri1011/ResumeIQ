/** Post-login redirect targets must stay on known app routes (no open redirects). */

const EXACT_PATHS = new Set([
  "/dashboard",
  "/register",
  "/resumes/upload",
  "/resumes/optimize/review",
  "/jobs/analyze",
  "/bullets/improve",
]);

const PREFIX_PATHS = ["/dashboard?", "/resumes/", "/jobs/", "/bullets/"];

export function getSafeNextPath(next: string | null | undefined): string {
  if (!next || !next.startsWith("/") || next.startsWith("//")) {
    return "/dashboard";
  }

  if (next === "/reg") {
    return "/register";
  }

  if (EXACT_PATHS.has(next.split("?")[0] ?? next)) {
    return next;
  }

  if (PREFIX_PATHS.some((prefix) => next.startsWith(prefix))) {
    return next;
  }

  return "/dashboard";
}
