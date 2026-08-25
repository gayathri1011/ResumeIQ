import Link from "next/link";
import { ArrowRight, FileSearch, Sparkles, Target } from "lucide-react";

import {
  BrandLockup,
  LaurelIcon,
  OrnamentDivider,
} from "@/components/brand/BrandMark";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const FEATURES = [
  {
    title: "Resume health scoring",
    description:
      "AI analysis across ATS, skills, experience, and content quality.",
    icon: FileSearch,
  },
  {
    title: "Semantic job matching",
    description:
      "Match your resume to job descriptions with embeddings, not keywords alone.",
    icon: Target,
  },
  {
    title: "AI optimization",
    description:
      "Role-targeted improvements with explainable before/after review.",
    icon: Sparkles,
  },
] as const;

export default function HomePage() {
  return (
    <main className="relative min-h-screen overflow-hidden">
      <div
        className="pointer-events-none absolute inset-0"
        aria-hidden="true"
        style={{
          backgroundImage: `
            radial-gradient(ellipse 70% 50% at 18% 8%, hsl(34 45% 90%), transparent 50%),
            radial-gradient(ellipse 55% 40% at 88% 0%, hsl(28 35% 88% / 0.85), transparent 45%),
            radial-gradient(ellipse 80% 50% at 50% 100%, hsl(34 28% 88% / 0.55), transparent 55%)
          `,
        }}
      />

      <div className="page-container relative">
        <header className="flex items-center justify-between py-4 fade-up">
          <BrandLockup href="/" />
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" className="rounded-full" asChild>
              <Link href="/login">Log in</Link>
            </Button>
            <Button size="sm" className="rounded-full" asChild>
              <Link href="/register">Sign up</Link>
            </Button>
          </div>
        </header>

        <section className="mx-auto max-w-3xl space-y-8 py-16 text-center sm:py-24">
          <div className="space-y-4 fade-up">
            <h1 className="font-display text-4xl font-semibold tracking-tight text-foreground sm:text-5xl md:text-[3.35rem]">
              ResumeIQ
            </h1>
            <p className="text-base font-medium tracking-wide text-primary sm:text-lg">
              Your resume is your story
            </p>
            <OrnamentDivider />
            <p className="mx-auto max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg">
              Upload your resume, understand your health score, match against
              real job descriptions, and optimize with explainable AI — all in
              one focused workspace.
            </p>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-3 fade-up fade-up-delay-1">
            <Button asChild size="lg">
              <Link href="/register">
                Get started
                <ArrowRight className="ml-1 h-4 w-4" aria-hidden="true" />
              </Link>
            </Button>
            <Button variant="outline" size="lg" asChild>
              <Link href="/login">Log in</Link>
            </Button>
          </div>
        </section>

        <section className="grid gap-4 pb-10 sm:grid-cols-3">
          {FEATURES.map((feature, index) => {
            const Icon = feature.icon;
            return (
              <Card
                key={feature.title}
                className={`fade-up fade-up-delay-${index + 1}`}
              >
                <CardHeader>
                  <div className="icon-orb mb-3 h-11 w-11">
                    <Icon className="h-4 w-4 text-primary" aria-hidden="true" />
                  </div>
                  <CardTitle className="text-section-title font-display">
                    {feature.title}
                  </CardTitle>
                  <CardDescription>{feature.description}</CardDescription>
                </CardHeader>
              </Card>
            );
          })}
        </section>

        <footer className="auth-quote pb-12">
          <LaurelIcon />
          <span>Your resume is your story. We help you tell it better.</span>
          <LaurelIcon className="scale-x-[-1]" />
        </footer>
      </div>
    </main>
  );
}
