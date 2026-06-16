import { NewRunDialog } from "@/components/runs/new-run-dialog";
import { RunsLibrary } from "@/components/runs/runs-library";

export default function RunsPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Runs</h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            Every batch detection run, scoped to this app&apos;s B2 prefix. Each
            run reads source media from B2 and writes annotated frames, instance
            crops, and a COCO dataset back.
          </p>
        </div>
        <NewRunDialog />
      </div>
      <div className="animate-fade-in-up stagger-2">
        <RunsLibrary />
      </div>
    </div>
  );
}
