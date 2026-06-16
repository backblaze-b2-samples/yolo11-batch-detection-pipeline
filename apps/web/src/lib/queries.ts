"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ApiError,
  createRun,
  deleteFile,
  deleteRun,
  getFiles,
  getFileStats,
  getPreviewUrl,
  getRun,
  getRunDetections,
  getRuns,
  getRunStats,
  getUploadActivity,
} from "@/lib/api-client";
import {
  ACTIVE_RUN_STATUSES,
  type CreateRunRequest,
  type FileMetadata,
  type Run,
  type RunSummary,
} from "@yolo11-batch-detection-pipeline/shared";

// Single source of truth for query keys. Keep these tightly scoped so that
// invalidating "files" doesn't blow away unrelated caches, and so an IDE
// "find usages" of `qk.files` reveals every consumer.
export const qk = {
  all: ["b2"] as const,
  files: (prefix?: string, limit?: number) =>
    [...qk.all, "files", prefix ?? "", limit ?? 100] as const,
  stats: () => [...qk.all, "stats"] as const,
  uploadActivity: (days: number) =>
    [...qk.all, "stats", "activity", days] as const,
  preview: (key: string) => [...qk.all, "preview", key] as const,
  runStats: () => [...qk.all, "run-stats"] as const,
  runs: () => [...qk.all, "runs"] as const,
  run: (id: string) => [...qk.all, "run", id] as const,
  runDetections: (id: string) => [...qk.all, "run", id, "detections"] as const,
};

// While any run is in flight, poll every 4s; stop once everything is terminal
// (ready/failed). Shared by the list, detail, and dashboard views.
const POLL_MS = 4000;

function anyActive(runs: { status: string }[] | undefined): boolean {
  return !!runs?.some((r) =>
    (ACTIVE_RUN_STATUSES as string[]).includes(r.status)
  );
}

export function useFiles(prefix = "", limit = 100) {
  return useQuery<FileMetadata[], ApiError>({
    queryKey: qk.files(prefix, limit),
    queryFn: () => getFiles(prefix, limit),
  });
}

export function useFileStats() {
  return useQuery({
    queryKey: qk.stats(),
    queryFn: getFileStats,
  });
}

export function useUploadActivity(days = 7) {
  return useQuery({
    queryKey: qk.uploadActivity(days),
    queryFn: () => getUploadActivity(days),
  });
}

// Presigned preview URL — only fetched when `enabled` is true (e.g., when
// the dialog opens for a specific file). Kept short-lived (60s) because
// the URL itself has a presigned expiry and is cheap to regenerate.
export function usePreviewUrl(key: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: qk.preview(key ?? ""),
    queryFn: () => getPreviewUrl(key as string),
    enabled: enabled && !!key,
    staleTime: 60_000,
  });
}

export function useDeleteFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (fileKey: string) => deleteFile(fileKey),
    // After delete, blow away every cached file list + stats. Cheap and
    // correct — the dashboard re-fetches lazily as components remount.
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}

// --- YOLO11 batch-detection pipeline ---

export function useRunStats() {
  return useQuery({
    queryKey: qk.runStats(),
    queryFn: getRunStats,
    refetchInterval: (q) => (anyActive(q.state.data?.recent) ? POLL_MS : false),
  });
}

export function useRuns() {
  return useQuery<RunSummary[], ApiError>({
    queryKey: qk.runs(),
    queryFn: getRuns,
    refetchInterval: (q) => (anyActive(q.state.data) ? POLL_MS : false),
  });
}

export function useRun(id: string) {
  return useQuery<Run, ApiError>({
    queryKey: qk.run(id),
    queryFn: () => getRun(id),
    enabled: !!id,
    refetchInterval: (q) =>
      anyActive(q.state.data ? [q.state.data] : undefined) ? POLL_MS : false,
  });
}

// Detections (with presigned annotated/crop URLs) are only meaningful once the
// run is ready, so callers pass `enabled` keyed on status.
export function useRunDetections(id: string, enabled: boolean) {
  return useQuery({
    queryKey: qk.runDetections(id),
    queryFn: () => getRunDetections(id),
    enabled: enabled && !!id,
    staleTime: 5 * 60_000,
  });
}

export function useCreateRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateRunRequest) => createRun(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.all }),
  });
}

export function useDeleteRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteRun(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.all }),
  });
}
