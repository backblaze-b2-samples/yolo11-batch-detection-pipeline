"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { ArrowLeft, Download, Info, ScanSearch, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { ErrorState } from "@/components/ui/error-state";
import { EmptyState } from "@/components/ui/empty-state";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { StatusBadge, isActive } from "./status-badge";
import { AnnotatedGallery, CropGallery } from "./detection-gallery";
import { getRunExportUrl } from "@/lib/api-client";
import { useDeleteRun, useRun, useRunDetections } from "@/lib/queries";

export function RunDetail({ runId }: { runId: string }) {
  const router = useRouter();
  const { data: run, isLoading, error, refetch } = useRun(runId);
  const ready = run?.status === "ready";
  const { data: view } = useRunDetections(runId, !!ready);
  const del = useDeleteRun();

  // Confidence-threshold slider — re-filters the structured results
  // client-side without re-running the model. Floored at the run's own
  // server-side min_confidence.
  const floor = run?.min_confidence ?? 0.1;
  const [threshold, setThreshold] = useState(0.25);
  const effective = Math.max(floor, threshold);

  const totals = useMemo(() => {
    const images = view?.images ?? [];
    let kept = 0;
    for (const img of images) kept += img.detections.filter((d) => d.score >= effective).length;
    return { images: images.length, kept };
  }, [view, effective]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="aspect-video w-full rounded-md" />
      </div>
    );
  }

  if (error || !run) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  const handleDelete = () => {
    del.mutate(runId, {
      onSuccess: () => {
        toast.success("Run and its artifacts deleted from B2");
        router.push("/runs");
      },
      onError: (e) => toast.error(`Delete failed: ${e.message}`),
    });
  };

  const handleExport = async () => {
    try {
      const { url } = await getRunExportUrl(runId);
      window.open(url, "_blank");
    } catch (e) {
      toast.error(`Export failed: ${(e as Error).message}`);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
        <div className="flex items-center gap-3 min-w-0">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 shrink-0"
            onClick={() => router.push("/runs")}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="min-w-0">
            <h1 className="page-title truncate">{run.name}</h1>
            <div className="mt-1 flex items-center gap-2">
              <StatusBadge status={run.status} />
              <span className="text-xs text-muted-foreground">
                {run.task} · {run.model} · {run.image_count} image
                {run.image_count === 1 ? "" : "s"}
              </span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleExport}
            disabled={!run.instances_key}
          >
            <Download className="h-3.5 w-3.5 mr-1.5" />
            Export COCO
          </Button>
          <Button variant="outline" size="sm" onClick={handleDelete} disabled={del.isPending}>
            <Trash2 className="h-3.5 w-3.5 mr-1.5" />
            Delete
          </Button>
        </div>
      </div>

      {run.status === "failed" && (
        <Alert variant="destructive">
          <Info className="h-4 w-4" />
          <AlertTitle>Run failed</AlertTitle>
          <AlertDescription>
            {run.error || "The pipeline did not complete."}
          </AlertDescription>
        </Alert>
      )}

      {isActive(run.status) ? (
        <Card>
          <CardContent className="p-0">
            <EmptyState
              icon={ScanSearch}
              title="Detection in progress…"
              description="YOLO11 is reading source media from B2, detecting, annotating, and writing crops + COCO JSON back. This page updates automatically."
            />
          </CardContent>
        </Card>
      ) : ready && view ? (
        <>
          <div className="rounded-lg border border-border p-4 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <label htmlFor="conf" className="text-sm font-medium">
                Confidence threshold{" "}
                <span className="tabular-nums text-muted-foreground">
                  {effective.toFixed(2)}
                </span>
              </label>
              <span className="text-xs text-muted-foreground tabular-nums">
                {totals.kept} detections across {totals.images} images
              </span>
            </div>
            <input
              id="conf"
              type="range"
              min={floor}
              max={0.95}
              step={0.05}
              value={effective}
              onChange={(e) => setThreshold(Number(e.target.value))}
              className="w-full accent-primary"
            />
            <p className="text-[11px] text-muted-foreground">
              Filters the stored detections client-side — no re-run needed. The
              run was detected at a floor of {floor.toFixed(2)}.
            </p>
          </div>

          <Tabs defaultValue="frames">
            <TabsList>
              <TabsTrigger value="frames">Annotated frames</TabsTrigger>
              <TabsTrigger value="crops">Instance crops</TabsTrigger>
            </TabsList>
            <TabsContent value="frames">
              <AnnotatedGallery images={view.images} threshold={effective} />
            </TabsContent>
            <TabsContent value="crops">
              <CropGallery images={view.images} threshold={effective} />
            </TabsContent>
          </Tabs>
        </>
      ) : (
        <Card>
          <CardContent className="p-0">
            <EmptyState
              icon={ScanSearch}
              title="No detections"
              description="This run produced no results. Check that the source prefix contains image or video media."
            />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
