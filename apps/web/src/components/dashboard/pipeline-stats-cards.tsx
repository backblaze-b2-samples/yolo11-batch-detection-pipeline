"use client";

import { ScanSearch, ImageIcon, Boxes, Tags } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { useRunStats } from "@/lib/queries";

export function PipelineStatsCards() {
  const { data: stats, isLoading, error, refetch } = useRunStats();

  if (error) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState error={error} onRetry={() => refetch()} />
        </CardContent>
      </Card>
    );
  }

  const cards = [
    { title: "Runs", value: stats?.runs ?? 0, icon: ScanSearch },
    { title: "Images Processed", value: stats?.images_processed ?? 0, icon: ImageIcon },
    { title: "Detections", value: stats?.detections ?? 0, icon: Boxes },
    { title: "Distinct Classes", value: stats?.distinct_classes ?? 0, icon: Tags },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card, i) => (
        <Card
          key={card.title}
          className={`card-hover animate-fade-in-up stagger-${i + 1}`}
        >
          <CardHeader className="flex flex-row items-center justify-between pt-4 pb-2 px-4 space-y-0">
            <CardTitle className="text-xs font-semibold text-muted-foreground">
              {card.title}
            </CardTitle>
            <div className="stat-icon-wrap">
              <card.icon className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="pb-5 px-4">
            {isLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div className="stat-value tabular-nums">{card.value}</div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
