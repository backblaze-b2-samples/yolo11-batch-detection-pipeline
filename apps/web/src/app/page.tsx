import { PipelineStatsCards } from "@/components/dashboard/pipeline-stats-cards";
import { FootprintCard } from "@/components/dashboard/footprint-card";
import { RecentRunsTable } from "@/components/dashboard/recent-runs-table";
import { NewRunDialog } from "@/components/runs/new-run-dialog";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            Your YOLO11 batch-detection pipeline at a glance — every run,
            detection, and crop is stored on Backblaze B2.
          </p>
        </div>
        <NewRunDialog />
      </div>
      <PipelineStatsCards />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="animate-fade-in-up stagger-3">
          <FootprintCard />
        </div>
        <div className="animate-fade-in-up stagger-4">
          <RecentRunsTable />
        </div>
      </div>
    </div>
  );
}
