"use client";

import { HardDrive, Scissors } from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { useRunStats } from "@/lib/queries";

/** The strategic B2 story: every run multiplies the stored footprint of the
 * source corpus (annotated frames + COCO JSON + N crops per detection), and B2
 * absorbs both the reads (source) and the writes (artifacts). */
export function FootprintCard() {
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

  const multiplier = stats?.footprint_multiplier ?? 0;
  const total = (stats?.source_bytes ?? 0) + (stats?.derived_bytes ?? 0);
  const derivedPct = total > 0 ? Math.round(((stats?.derived_bytes ?? 0) / total) * 100) : 0;

  return (
    <Card className="h-full">
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title flex items-center gap-2">
          <HardDrive className="h-4 w-4 text-muted-foreground" />
          B2 storage footprint
        </CardTitle>
      </CardHeader>
      <CardContent className="p-5 space-y-5">
        {isLoading ? (
          <Skeleton className="h-24 w-full" />
        ) : (
          <>
            <div>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-display font-bold tabular-nums">
                  {multiplier.toFixed(2)}×
                </span>
                <span className="text-sm text-muted-foreground">
                  derived-to-source footprint multiplier
                </span>
              </div>
              <p className="mt-1 text-[11px] text-muted-foreground flex items-center gap-1">
                <Scissors className="h-3 w-3" />
                {stats?.crops_generated ?? 0} crops generated across all runs
              </p>
            </div>

            <div className="space-y-2">
              <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-primary"
                  style={{ width: `${derivedPct}%` }}
                />
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">
                  Source read:{" "}
                  <span className="font-mono tabular-nums text-foreground">
                    {stats?.source_bytes_human ?? "0 B"}
                  </span>
                </span>
                <span className="text-muted-foreground">
                  Derived written:{" "}
                  <span className="font-mono tabular-nums text-foreground">
                    {stats?.derived_bytes_human ?? "0 B"}
                  </span>
                </span>
              </div>
            </div>

            <p className="text-[11px] text-muted-foreground leading-relaxed">
              Each batch run reads the source corpus from B2 and writes annotated
              frames, instance crops, and COCO JSON back — so B2 absorbs both the
              sustained read and the growing derived-dataset write traffic.
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}
