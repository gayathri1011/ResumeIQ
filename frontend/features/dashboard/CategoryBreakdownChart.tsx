"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { LatestJobMatchSummary, ResumeAnalysis } from "@/types/analysis";
import { CATEGORY_CONFIG } from "@/types/analysis";
import { getCategoryScore } from "@/features/dashboard/utils";

interface CategoryBreakdownChartProps {
  analysis: ResumeAnalysis;
  jobMatch?: LatestJobMatchSummary | null;
}

export function CategoryBreakdownChart({
  analysis,
  jobMatch,
}: CategoryBreakdownChartProps) {
  const data = CATEGORY_CONFIG.map((category) => {
    const score =
      category.key === "job_match"
        ? (jobMatch?.match_score ?? null)
        : getCategoryScore(analysis, category.key);
    return {
      name: category.label.split(" ")[0],
      fullName: category.label,
      score: score ?? 0,
      hasScore: score !== null,
    };
  }).filter((item) => item.hasScore);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Category breakdown</CardTitle>
        <CardDescription>
          Resume health and job match scores from your latest analysis
        </CardDescription>
      </CardHeader>
      <CardContent className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
            <Tooltip
              formatter={(value: number) => [`${value} / 100`, "Score"]}
              labelFormatter={(_, payload) =>
                payload?.[0]?.payload?.fullName ?? ""
              }
            />
            <Bar dataKey="score" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
