"use client";

import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";

import {
  BrandLockup,
  BrandMark,
  LaurelIcon,
  OrnamentDivider,
} from "@/components/brand/BrandMark";
import { cn } from "@/lib/utils";

interface AuthShellProps {
  children: React.ReactNode;
  title: string;
  subtitle: string;
  footer?: React.ReactNode;
  className?: string;
}

export function AuthShell({
  children,
  title,
  subtitle,
  footer,
  className,
}: AuthShellProps) {
  return (
    <main className="relative min-h-screen overflow-hidden bg-cream">
      <div
        className="pointer-events-none absolute inset-0"
        aria-hidden="true"
        style={{
          backgroundImage: `
            radial-gradient(ellipse 70% 50% at 15% 20%, hsl(34 45% 88% / 0.95), transparent 55%),
            radial-gradient(ellipse 60% 45% at 85% 15%, hsl(28 35% 86% / 0.8), transparent 50%),
            radial-gradient(ellipse 80% 55% at 50% 100%, hsl(36 30% 90% / 0.7), transparent 55%),
            linear-gradient(165deg, hsl(36 42% 95%), hsl(34 35% 92%) 45%, hsl(32 30% 90%))
          `,
        }}
      />

      <header className="relative z-20 flex items-center justify-between px-5 py-5 sm:px-8">
        <BrandLockup href="/" />
        <span className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-gradient-to-b from-card to-sand/50 px-3.5 py-2 text-sm font-medium text-foreground shadow-[inset_0_1px_0_rgba(255,255,255,0.85),0_8px_18px_-12px_rgba(55,38,18,0.35)]">
          <Sparkles className="h-3.5 w-3.5 text-gold" aria-hidden="true" />
          AI Mode
        </span>
      </header>

      <div className="relative z-10 flex min-h-[calc(100vh-8rem)] flex-col items-center justify-center px-4 pb-10 pt-2">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.18, ease: "easeOut" }}
          className={cn("panel-3d w-full max-w-[440px] p-7 sm:p-9", className)}
        >
          <div className="mb-2 flex flex-col items-center text-center">
            <BrandMark size="lg" className="mb-4" />
            <h1 className="font-display text-2xl font-semibold tracking-tight text-foreground sm:text-[1.75rem]">
              {title}
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">{subtitle}</p>
            <OrnamentDivider className="mt-4" />
          </div>

          {children}

          {footer ? (
            <div className="mt-6 text-center text-sm text-muted-foreground">
              {footer}
            </div>
          ) : null}
        </motion.div>

        <p className="auth-quote mt-10 max-w-md px-4">
          <LaurelIcon />
          <span>Your resume is your story. We help you tell it better.</span>
          <LaurelIcon className="scale-x-[-1]" />
        </p>
      </div>
    </main>
  );
}
