export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  // Image-specific
  image_width: number | null;
  image_height: number | null;
  exif: Record<string, string> | null;
  // PDF-specific
  pdf_pages: number | null;
  pdf_author: string | null;
  pdf_title: string | null;
  // Audio/Video
  duration_seconds: number | null;
  codec: string | null;
  bitrate: number | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// --- YOLO11 batch-detection pipeline ---

export type RunStatus =
  | "queued"
  | "listing"
  | "detecting"
  | "annotating"
  | "cropping"
  | "ready"
  | "failed";

export const ACTIVE_RUN_STATUSES: RunStatus[] = [
  "queued",
  "listing",
  "detecting",
  "annotating",
  "cropping",
];

export type DetectionTask = "detect" | "segment";

export interface Detection {
  category_id: number;
  class_name: string;
  score: number;
  bbox: [number, number, number, number]; // [x, y, w, h] absolute pixels
  has_mask: boolean;
}

export interface ImageResult {
  stem: string;
  source_key: string;
  width: number;
  height: number;
  detections: Detection[];
  annotated_key: string | null;
  coco_key: string | null;
  crop_keys: string[];
  frame_t: number | null;
}

export interface Run {
  id: string;
  name: string;
  source_prefix: string;
  task: DetectionTask;
  model: string;
  min_confidence: number;
  status: RunStatus;
  error: string | null;
  images: ImageResult[];
  image_count: number;
  detection_count: number;
  crop_count: number;
  class_counts: Record<string, number>;
  source_bytes: number;
  derived_bytes: number;
  instances_key: string | null;
  created_at: string;
  updated_at: string;
}

export interface RunSummary {
  id: string;
  name: string;
  status: RunStatus;
  task: DetectionTask;
  image_count: number;
  detection_count: number;
  crop_count: number;
  thumb_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface RunStats {
  runs: number;
  images_processed: number;
  detections: number;
  crops_generated: number;
  distinct_classes: number;
  source_bytes: number;
  source_bytes_human: string;
  derived_bytes: number;
  derived_bytes_human: string;
  footprint_multiplier: number;
  recent: RunSummary[];
}

/** Per-image detection view returned by GET /runs/{id}/detections — carries
 * presigned URLs for the annotated frame and instance crops. */
export interface DetectionImageView {
  stem: string;
  source_key: string;
  width: number;
  height: number;
  frame_t: number | null;
  annotated_url: string | null;
  detections: Detection[];
  crop_urls: string[];
}

export interface RunDetectionsView {
  id: string;
  name: string;
  task: DetectionTask;
  min_confidence: number;
  class_counts: Record<string, number>;
  images: DetectionImageView[];
}

export interface CreateRunRequest {
  name: string;
  source_prefix: string;
  task: DetectionTask;
  model?: string | null;
  min_confidence: number;
}
