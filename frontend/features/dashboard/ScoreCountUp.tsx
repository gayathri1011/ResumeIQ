"use client";

import { useEffect, useState } from "react";
import { animate } from "framer-motion";

import { scoreColor } from "@/features/dashboard/utils";
import { cn } from "@/lib/utils";

interface ScoreCountUpProps {
  value: number;
  className?: string;
}

export function ScoreCountUp({ value, className }: ScoreCountUpProps) {
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    const controls = animate(0, value, {
      duration: 0.35,
      ease: "easeOut",
      onUpdate: (latest) => setDisplay(Math.round(latest)),
    });
    return controls.stop;
  }, [value]);

  return (
    <span className={cn("tabular-nums", scoreColor(value), className)}>
      {display}
    </span>
  );
}
