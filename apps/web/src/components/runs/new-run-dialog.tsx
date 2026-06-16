"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useCreateRun } from "@/lib/queries";
import type { DetectionTask } from "@yolo11-batch-detection-pipeline/shared";

const DEFAULT_PREFIX = "yolo11-batch-detection-pipeline/source/";

export function NewRunDialog() {
  const router = useRouter();
  const create = useCreateRun();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [sourcePrefix, setSourcePrefix] = useState(DEFAULT_PREFIX);
  const [task, setTask] = useState<DetectionTask>("detect");
  const [confidence, setConfidence] = useState(0.25);

  const submit = () => {
    create.mutate(
      {
        name,
        source_prefix: sourcePrefix,
        task,
        min_confidence: confidence,
      },
      {
        onSuccess: (run) => {
          toast.success("Run started — detection is processing on the server");
          setOpen(false);
          setName("");
          router.push(`/runs/${run.id}`);
        },
        onError: (e) => toast.error(`Could not start run: ${e.message}`),
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" className="h-8">
          <Plus className="h-3.5 w-3.5" />
          New Run
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New detection run</DialogTitle>
          <DialogDescription>
            Point YOLO11 at a B2 source prefix. The pipeline reads the media,
            runs detection locally, and writes COCO JSON, annotated frames, and
            instance crops back to B2.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-1.5">
            <Label htmlFor="run-name">Run name</Label>
            <Input
              id="run-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. street-scene batch"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="run-prefix">B2 source prefix</Label>
            <Input
              id="run-prefix"
              value={sourcePrefix}
              onChange={(e) => setSourcePrefix(e.target.value)}
              placeholder={DEFAULT_PREFIX}
              className="font-mono text-xs"
            />
            <p className="text-[11px] text-muted-foreground">
              Images and short videos under this prefix become the run input.
              Defaults to media you uploaded.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>Task</Label>
              <Select
                value={task}
                onValueChange={(v) => setTask(v as DetectionTask)}
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="detect">Detect (boxes)</SelectItem>
                  <SelectItem value="segment">Segment (masks)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="run-conf">
                Min confidence{" "}
                <span className="text-muted-foreground tabular-nums">
                  {confidence.toFixed(2)}
                </span>
              </Label>
              <input
                id="run-conf"
                type="range"
                min={0.1}
                max={0.9}
                step={0.05}
                value={confidence}
                onChange={(e) => setConfidence(Number(e.target.value))}
                className="w-full accent-primary"
              />
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => setOpen(false)}
            disabled={create.isPending}
          >
            Cancel
          </Button>
          <Button onClick={submit} disabled={create.isPending}>
            {create.isPending ? "Starting…" : "Start run"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
