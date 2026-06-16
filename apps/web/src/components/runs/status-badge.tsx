"use client";

import { Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  ACTIVE_RUN_STATUSES,
  type RunStatus,
} from "@yolo11-batch-detection-pipeline/shared";

const LABELS: Record<RunStatus, string> = {
  queued: "Queued",
  listing: "Listing media",
  detecting: "Detecting",
  annotating: "Annotating",
  cropping: "Writing dataset",
  ready: "Ready",
  failed: "Failed",
};

export function isActive(status: RunStatus): boolean {
  return (ACTIVE_RUN_STATUSES as RunStatus[]).includes(status);
}

export function StatusBadge({ status }: { status: RunStatus }) {
  const active = isActive(status);
  const variant =
    status === "ready"
      ? "default"
      : status === "failed"
        ? "destructive"
        : "secondary";

  return (
    <Badge variant={variant} className="gap-1.5">
      {active && <Loader2 className="h-3 w-3 animate-spin" />}
      {LABELS[status]}
    </Badge>
  );
}
