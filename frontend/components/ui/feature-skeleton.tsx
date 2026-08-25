import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

interface FeatureSkeletonProps {
  titleWidth?: string;
  cardHeight?: string;
  cards?: number;
}

export function FeatureSkeleton({
  titleWidth = "w-64",
  cardHeight = "h-80",
  cards = 1,
}: FeatureSkeletonProps) {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Skeleton className={`h-8 ${titleWidth}`} />
        <Skeleton className="h-4 w-96 max-w-full" />
      </div>
      {Array.from({ length: cards }).map((_, index) => (
        <Card key={index}>
          <CardHeader className="space-y-2">
            <Skeleton className="h-5 w-40" />
            <Skeleton className="h-4 w-72 max-w-full" />
          </CardHeader>
          <CardContent>
            <Skeleton className={`w-full ${cardHeight}`} />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
