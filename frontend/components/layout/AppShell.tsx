"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import {
  BotMessageSquare,
  Briefcase,
  ChevronLeft,
  ChevronRight,
  Compass,
  Eye,
  LayoutDashboard,
  LogOut,
  Menu,
  TrendingUp,
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
  { href: "/interview", label: "Interview", icon: BotMessageSquare },
  { href: "/growth", label: "Career Growth", icon: TrendingUp },
  { href: "/career-trajectory", label: "Career trajectory", icon: Compass },
  { href: "/recruiter-lens", label: "Recruiter Lens", icon: Eye },
] as const;

interface AppShellProps {
  children: React.ReactNode;
  className?: string;
}

export function AppShell({ children, className }: AppShellProps) {
  const pathname = usePathname();
  const { logout, user } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [trajectoryHref, setTrajectoryHref] = useState("/career-trajectory");
  const [recruiterLensHref, setRecruiterLensHref] = useState("/recruiter-lens");
  const [growthHref, setGrowthHref] = useState("/growth");

  const navRef = useRef<HTMLElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  const checkScroll = useCallback(() => {
    const el = navRef.current;
    if (!el) return;
    const hasOverflow = el.scrollWidth > el.clientWidth;
    if (!hasOverflow) {
      setCanScrollLeft(false);
      setCanScrollRight(false);
      return;
    }
    setCanScrollLeft(el.scrollLeft > 2);
    setCanScrollRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 2);
  }, []);

  const handleScrollLeft = () => {
    navRef.current?.scrollBy({ left: -200, behavior: "smooth" });
  };

  const handleScrollRight = () => {
    navRef.current?.scrollBy({ left: 200, behavior: "smooth" });
  };

  useEffect(() => {
    const el = navRef.current;
    if (!el) return;

    checkScroll();
    el.addEventListener("scroll", checkScroll, { passive: true });
    window.addEventListener("resize", checkScroll);

    const resizeObserver = new ResizeObserver(() => {
      checkScroll();
    });
    resizeObserver.observe(el);

    return () => {
      el.removeEventListener("scroll", checkScroll);
      window.removeEventListener("resize", checkScroll);
      resizeObserver.disconnect();
    };
  }, [checkScroll]);

  useEffect(() => {
    const el = navRef.current;
    if (!el) return;

    const timer = setTimeout(() => {
      const activeEl = el.querySelector<HTMLElement>('[data-active="true"]');
      if (activeEl) {
        activeEl.scrollIntoView({
          behavior: "smooth",
          block: "nearest",
          inline: "nearest",
        });
      }
      checkScroll();
    }, 100);

    return () => clearTimeout(timer);
  }, [pathname, checkScroll]);

  useEffect(() => {
    if (window.location.search) {
      setTrajectoryHref(`/career-trajectory${window.location.search}`);
      setRecruiterLensHref(`/recruiter-lens${window.location.search}`);
      setGrowthHref(`/growth${window.location.search}`);
    }
  }, []);

  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(`${href}/`);

  const navLink = (
    item: (typeof NAV_ITEMS)[number],
    onNavigate?: () => void,
    isMobile = false,
  ) => {
    const Icon = item.icon;
    const active = isActive(item.href);
    const href =
      item.href === "/career-trajectory"
        ? trajectoryHref
        : item.href === "/recruiter-lens"
          ? recruiterLensHref
          : item.href === "/growth"
            ? growthHref
            : item.href;
    return (
      <Link
        key={item.href}
        href={href}
        onClick={onNavigate}
        data-active={active}
        className={cn(
          "nav-pill relative inline-flex shrink-0 items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-muted-foreground transition-[color,transform] duration-100 ease-out active:scale-[0.97] xl:px-3.5 xl:py-2 xl:text-sm",
          isMobile && "w-full justify-start py-2.5 text-sm",
        )}
        aria-current={active ? "page" : undefined}
      >
        <Icon className="h-3.5 w-3.5 shrink-0 opacity-80" aria-hidden="true" />
        <span className="whitespace-nowrap">{item.label}</span>
        {active ? (
          <motion.span
            layoutId={isMobile ? "nav-active-mobile" : "nav-active-desktop"}
            className="absolute inset-0 -z-10 rounded-full border border-primary/15 bg-gradient-to-b from-card to-sand/60 shadow-[inset_0_1px_0_rgba(255,255,255,0.8),0_6px_14px_-10px_rgba(55,38,18,0.35)]"
            transition={{ type: "spring", stiffness: 520, damping: 34 }}
          />
        ) : null}
      </Link>
    );
  };

  return (
    <div className="relative min-h-screen overflow-x-clip">
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
        <div className="page-container flex h-16 min-w-0 items-center justify-between gap-3 py-0">
          <div className="flex shrink-0 items-center gap-3">
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
            <BrandLockup className="shrink-0" />
          </div>

          <div className="nav-shell-3d relative hidden min-w-0 max-w-full shrink items-center rounded-full p-1 lg:flex">
            {canScrollLeft && (
              <>
                <div
                  className="pointer-events-none absolute left-0 top-0 bottom-0 w-8 rounded-l-full bg-gradient-to-r from-card via-card/80 to-transparent z-10"
                  aria-hidden="true"
                />
                <button
                  type="button"
                  aria-label="Scroll navigation left"
                  onClick={handleScrollLeft}
                  className="absolute left-1 z-20 flex h-7 w-7 items-center justify-center rounded-full border border-primary/25 bg-gradient-to-b from-card to-sand/60 text-muted-foreground shadow-[inset_0_1px_0_rgba(255,255,255,0.8),0_4px_10px_-4px_rgba(55,38,18,0.35)] transition-all hover:border-primary/40 hover:text-foreground active:scale-95"
                >
                  <ChevronLeft className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                </button>
              </>
            )}

            <nav
              ref={navRef}
              className="flex min-w-0 max-w-full items-center gap-0.5 overflow-x-auto [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden rounded-full scroll-smooth"
              aria-label="Main navigation"
            >
              {NAV_ITEMS.map((item) => navLink(item))}
            </nav>

            {canScrollRight && (
              <>
                <div
                  className="pointer-events-none absolute right-0 top-0 bottom-0 w-8 rounded-r-full bg-gradient-to-l from-card via-card/80 to-transparent z-10"
                  aria-hidden="true"
                />
                <button
                  type="button"
                  aria-label="Scroll navigation right"
                  onClick={handleScrollRight}
                  className="absolute right-1 z-20 flex h-7 w-7 items-center justify-center rounded-full border border-primary/25 bg-gradient-to-b from-card to-sand/60 text-muted-foreground shadow-[inset_0_1px_0_rgba(255,255,255,0.8),0_4px_10px_-4px_rgba(55,38,18,0.35)] transition-all hover:border-primary/40 hover:text-foreground active:scale-95"
                >
                  <ChevronRight className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                </button>
              </>
            )}
          </div>

          <div className="flex shrink-0 items-center gap-2">
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
              className="max-h-[calc(100vh-4rem)] overflow-y-auto border-t border-border/50 bg-background/95 backdrop-blur-md lg:hidden"
              aria-label="Mobile navigation"
            >
              <div className="flex flex-col gap-1 px-4 py-3">
                {NAV_ITEMS.map((item) =>
                  navLink(item, () => setMobileOpen(false), true),
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
