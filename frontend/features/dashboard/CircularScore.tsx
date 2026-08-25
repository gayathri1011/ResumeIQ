"use client";

import { useId } from "react";
import { motion } from "framer-motion";

import { cn } from "@/lib/utils";
import { scoreStrokeColor } from "@/features/dashboard/utils";

interface CircularScoreProps {
  score: number | null;
  size?: number;
  strokeWidth?: number;
  label?: string;
  animate?: boolean;
  className?: string;
}

export function CircularScore({
  score,
  size = 140,
  strokeWidth = 10,
  label,
  animate: shouldAnimate = true,
  className,
}: CircularScoreProps) {
  const gradientId = useId().replace(/:/g, "");
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = score !== null ? score / 100 : 0;
  const offset = circumference * (1 - progress);
  const stroke = score !== null ? scoreStrokeColor(score) : "hsl(var(--muted-foreground))";

  return (
    <div
      className={cn(
        "relative inline-flex items-center justify-center rounded-full",
        className,
      )}
      style={{
        width: size,
        height: size,
        boxShadow:
          size >= 100
            ? "inset 0 1px 0 rgba(255,255,255,0.75), inset 0 -2px 6px rgba(70,45,15,0.08)"
            : undefined,
      }}
    >
      <svg width={size} height={size} className="-rotate-90">
        <defs>
          <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={stroke} stopOpacity="0.85" />
            <stop offset="100%" stopColor={stroke} stopOpacity="1" />
          </linearGradient>
        </defs>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="hsl(var(--muted))"
          strokeWidth={strokeWidth}
        />
        {score !== null && (
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={`url(#${gradientId})`}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={shouldAnimate ? { strokeDashoffset: circumference } : false}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 0.35, ease: "easeOut" }}
            style={{ filter: "drop-shadow(0 2px 4px rgba(55,38,18,0.18))" }}
          />
        )}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        {label && (
          <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
            {label}
          </span>
        )}
        {score !== null ? (
          <span className="text-2xl font-semibold tabular-nums">{score}</span>
        ) : (
          <span className="text-sm text-muted-foreground">—</span>
        )}
      </div>
    </div>
  );
}
