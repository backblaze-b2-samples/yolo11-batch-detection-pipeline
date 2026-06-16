"use client";

import Link from "next/link";
import Image from "next/image";
import { ScanSearch, ImageIcon, Boxes, Scissors } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { StatusBadge } from "./status-badge";
import { useRuns } from "@/lib/queries";
import { formatDate } from "@/lib/utils";

export function RunsLibrary() {
  const { data: runs = [], isLoading, error, refetch } = useRuns();

  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-56 w-full rounded-md" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState error={error} onRetry={() => refetch()} />
        </CardContent>
      </Card>
    );
  }

  if (runs.length === 0) {
    return (
      <Card>
        <CardContent className="p-0">
          <EmptyState
            icon={ScanSearch}
            title="No runs yet"
            description="Start a detection run against a B2 source prefix to populate this library."
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {runs.map((r) => (
        <Link key={r.id} href={`/runs/${r.id}`} className="group">
          <Card className="card-hover overflow-hidden h-full">
            <div className="relative aspect-video bg-muted overflow-hidden">
              {r.thumb_url ? (
                <Image
                  src={r.thumb_url}
                  alt={r.name}
                  fill
                  unoptimized
                  className="object-cover transition-transform group-hover:scale-105"
                />
              ) : (
                <div className="flex h-full items-center justify-center">
                  <ImageIcon className="h-8 w-8 text-muted-foreground" />
                </div>
              )}
              <div className="absolute top-2 right-2">
                <StatusBadge status={r.status} />
              </div>
              <div className="absolute bottom-2 left-2">
                <span className="rounded bg-background/80 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide">
                  {r.task}
                </span>
              </div>
            </div>
            <CardContent className="p-4 space-y-2">
              <p className="text-sm font-semibold truncate">{r.name}</p>
              <div className="flex items-center justify-between text-xs text-muted-foreground tabular-nums">
                <span className="inline-flex items-center gap-1">
                  <ImageIcon className="h-3.5 w-3.5" />
                  {r.image_count}
                </span>
                <span className="inline-flex items-center gap-1">
                  <Boxes className="h-3.5 w-3.5" />
                  {r.detection_count}
                </span>
                <span className="inline-flex items-center gap-1">
                  <Scissors className="h-3.5 w-3.5" />
                  {r.crop_count}
                </span>
              </div>
              <p className="text-[11px] text-muted-foreground">
                {formatDate(r.created_at)}
              </p>
            </CardContent>
          </Card>
        </Link>
      ))}
    </div>
  );
}
