import Link from "next/link";

import { APP_NAME } from "@/lib/constants";
import { cn } from "@/lib/utils";

interface BrandMarkProps {
  className?: string;
  size?: "sm" | "md" | "lg";
}

/** Unique ResumeIQ seal: resume page + gold IQ spark */
function LogoGlyph({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 48 48"
      fill="none"
      className={cn("h-[58%] w-[58%]", className)}
      aria-hidden="true"
    >
      {/* Resume page */}
      <path
        d="M15 10.5h13.2c.7 0 1.3.3 1.7.8l4.3 5.1c.4.5.6 1.1.6 1.7V36c0 1.4-1.1 2.5-2.5 2.5H15c-1.4 0-2.5-1.1-2.5-2.5V13c0-1.4 1.1-2.5 2.5-2.5Z"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      {/* Folded corner */}
      <path
        d="M28.5 10.5v5.2c0 .9.7 1.6 1.6 1.6h5.1"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Resume lines */}
      <path
        d="M18.5 22.5h11M18.5 27h14M18.5 31.5h9"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      {/* Gold IQ spark */}
      <path
        d="M36.2 15.2 37.5 12l1.3 3.2 3.2 1.3-3.2 1.3-1.3 3.2-1.3-3.2-3.2-1.3 3.2-1.3Z"
        fill="hsl(var(--gold))"
      />
    </svg>
  );
}

export function BrandMark({ className, size = "md" }: BrandMarkProps) {
  const sizeClass =
    size === "sm" ? "h-9 w-9" : size === "lg" ? "h-14 w-14" : "h-12 w-12";

  return (
    <span
      className={cn(
        "brand-mark text-foreground",
        sizeClass,
        className,
      )}
      aria-hidden="true"
    >
      <LogoGlyph />
    </span>
  );
}

interface BrandLockupProps {
  href?: string;
  className?: string;
  showWordmark?: boolean;
}

export function BrandLockup({
  href = "/dashboard",
  className,
  showWordmark = true,
}: BrandLockupProps) {
  const content = (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <BrandMark size="sm" />
      {showWordmark ? (
        <span className="font-display text-lg font-semibold tracking-tight text-foreground">
          {APP_NAME}
        </span>
      ) : null}
    </span>
  );

  if (!href) return content;
  return (
    <Link href={href} className="transition-opacity duration-100 hover:opacity-80">
      {content}
    </Link>
  );
}

export function OrnamentDivider({ className }: { className?: string }) {
  return (
    <div className={cn("ornament-divider", className)} aria-hidden="true">
      <span />
    </div>
  );
}

export function LaurelIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      className={className}
      aria-hidden="true"
    >
      <path
        d="M12 20c-2.2-1.4-4.8-4.2-5.5-8.2C5.7 7.2 8.2 4 12 3c3.8 1 6.3 4.2 5.5 8.8-.7 4-3.3 6.8-5.5 8.2Z"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
      <path
        d="M12 7.5c-1.4.8-2.5 2.4-2.8 4.2M12 7.5c1.4.8 2.5 2.4 2.8 4.2M12 12.2c-1 .6-1.7 1.6-1.9 2.8M12 12.2c1 .6 1.7 1.6 1.9 2.8"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
    </svg>
  );
}
