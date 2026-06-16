"use client";

import Image from "next/image";
import { Boxes } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { DetectionImageView } from "@yolo11-batch-detection-pipeline/shared";

/** A grid of annotated frames; each card shows how many detections survive the
 * current confidence threshold (computed by the parent). */
export function AnnotatedGallery({
  images,
  threshold,
}: {
  images: DetectionImageView[];
  threshold: number;
}) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {images.map((img) => {
        const kept = img.detections.filter((d) => d.score >= threshold).length;
        return (
          <Card key={img.stem} className="overflow-hidden">
            <div className="relative aspect-video bg-muted">
              {img.annotated_url ? (
                <Image
                  src={img.annotated_url}
                  alt={img.stem}
                  fill
                  unoptimized
                  className="object-contain"
                />
              ) : (
                <div className="flex h-full items-center justify-center">
                  <Boxes className="h-8 w-8 text-muted-foreground" />
                </div>
              )}
            </div>
            <CardContent className="p-3 flex items-center justify-between gap-2">
              <span className="truncate text-xs font-mono">{img.stem}</span>
              <Badge variant="secondary" className="tabular-nums shrink-0">
                {kept} det
              </Badge>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

interface Crop {
  url: string;
  className: string;
  score: number;
  key: string;
}

/** A per-class grouped grid of instance crops, filtered by confidence. The
 * crop_urls line up with the detections sorted by score (server-side), so we
 * pair them positionally. */
export function CropGallery({
  images,
  threshold,
}: {
  images: DetectionImageView[];
  threshold: number;
}) {
  const byClass = new Map<string, Crop[]>();
  for (const img of images) {
    const ordered = [...img.detections].sort((a, b) => b.score - a.score);
    img.crop_urls.forEach((url, i) => {
      const det = ordered[i];
      if (!det || det.score < threshold) return;
      const list = byClass.get(det.class_name) ?? [];
      list.push({ url, className: det.class_name, score: det.score, key: `${img.stem}-${i}` });
      byClass.set(det.class_name, list);
    });
  }

  const classes = [...byClass.entries()].sort((a, b) => b[1].length - a[1].length);

  if (classes.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No crops at this confidence threshold.
      </p>
    );
  }

  return (
    <div className="space-y-6">
      {classes.map(([className, crops]) => (
        <div key={className} className="space-y-2">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold capitalize">{className}</h3>
            <Badge variant="outline" className="tabular-nums">
              {crops.length}
            </Badge>
          </div>
          <div className="grid grid-cols-3 gap-2 sm:grid-cols-5 lg:grid-cols-8">
            {crops.map((c) => (
              <div
                key={c.key}
                className="relative aspect-square overflow-hidden rounded-md bg-muted"
                title={`${c.className} ${(c.score * 100).toFixed(0)}%`}
              >
                <Image src={c.url} alt={c.className} fill unoptimized className="object-cover" />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
