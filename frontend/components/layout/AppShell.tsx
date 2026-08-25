"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import {
  Briefcase,
  LayoutDashboard,
  LogOut,
  Menu,
  Sparkles,
  Upload,
  X,
} from "lucide-react";

import { BrandLockup } from "@/components/brand/BrandMark";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/features/auth/AuthProvider";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/resumes/upload", label: "Upload", icon: Upload },
  { href: "/jobs/analyze", label: "Job match", icon: Briefcase },
  { href: "/bullets/improve", label: "Bullets", icon: Sparkles },
] as const;

interface AppShellProps {
  children: React.ReactNode;
  className?: string;
}

export function AppShell({ children, className }: AppShellProps) {
  const pathname = usePathname();
  const { logout, user } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(`${href}/`);

  const navLink = (
    item: (typeof NAV_ITEMS)[number],
    onNavigate?: () => void,
  ) => {
    const Icon = item.icon;
    const active = isActive(item.href);
    return (
      <Link
        key={item.href}
        href={item.href}
        onClick={onNavigate}
        data-active={active}
        className="nav-pill relative inline-flex items-center gap-2"
        aria-current={active ? "page" : undefined}
      >
        <Icon className="h-3.5 w-3.5 shrink-0 opacity-80" aria-hidden="true" />
        {item.label}
        {active ? (
          <motion.span
            layoutId="nav-active"
            className="absolute inset-0 -z-10 rounded-full border border-primary/15 bg-gradient-to-b from-card to-sand/60 shadow-[inset_0_1px_0_rgba(255,255,255,0.8),0_6px_14px_-10px_rgba(55,38,18,0.35)]"
            transition={{ type: "spring", stiffness: 520, damping: 34 }}
          />
        ) : null}
      </Link>
    );
  };

  return (
    <div className="relative min-h-screen">
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-[30rem]"
        aria-hidden="true"
        style={{
          backgroundImage: `
            radial-gradient(ellipse 80% 55% at 50% -10%, hsl(36 48% 90% / 0.95), transparent 70%),
            radial-gradient(ellipse 45% 40% at 12% 8%, hsl(32 40% 88% / 0.55), transparent 60%)
          `,
        }}
      />

      <header className="header-3d sticky top-0 z-40">
        <div className="page-container flex h-16 items-center justify-between gap-4 py-0">
          <div className="flex items-center gap-3">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="rounded-full lg:hidden"
              aria-label={
                mobileOpen ? "Close navigation menu" : "Open navigation menu"
              }
              aria-expanded={mobileOpen}
              onClick={() => setMobileOpen((open) => !open)}
            >
              {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </Button>
            <BrandLockup />
          </div>

          <nav
            className="nav-shell-3d hidden items-center gap-1 rounded-full p-1 lg:flex"
            aria-label="Main navigation"
          >
            {NAV_ITEMS.map((item) => navLink(item))}
          </nav>

          <div className="flex items-center gap-2">
            {user?.full_name ? (
              <span className="hidden max-w-[10rem] truncate text-sm text-muted-foreground sm:inline">
                {user.full_name}
              </span>
            ) : null}
            <Button
              variant="soft"
              size="sm"
              onClick={() => void logout()}
              aria-label="Log out"
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">Log out</span>
            </Button>
          </div>
        </div>

        <AnimatePresence>
          {mobileOpen ? (
            <motion.nav
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.15, ease: [0.22, 1, 0.36, 1] }}
              className="overflow-hidden border-t border-border/50 lg:hidden"
              aria-label="Mobile navigation"
            >
              <div className="flex flex-col gap-1 px-4 py-3">
                {NAV_ITEMS.map((item) =>
                  navLink(item, () => setMobileOpen(false)),
                )}
              </div>
            </motion.nav>
          ) : null}
        </AnimatePresence>
      </header>

      <div className={cn("page-container relative", className)}>{children}</div>
    </div>
  );
}
