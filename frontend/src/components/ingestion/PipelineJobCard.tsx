import { AlertTriangle, Loader2, FileText, RotateCcw, X } from "lucide-react";
import StatusBadge from "../common/StatusBadge";
import StageDots from "./StageDots";
import { BORDER, MUTED, TEXT, RED, BLUE, NAVY } from "../../theme/theme";

// Types defined locally to avoid runtime import issues from theme.ts
export type JobStatus = "queued" | "processing" | "completed" | "failed" | "verified";

export interface Job {
  id: number;
  name: string;
  meta: string;
  stageIndex: number;
  status: JobStatus;
  error?: string;
}

interface PipelineJobCardProps {
  job: Job;
  onRetry: (id: number) => void;
  onIgnore: (id: number) => void;
}

export default function PipelineJobCard({ job, onRetry, onIgnore }: PipelineJobCardProps) {
  return (
    <div
      className="rounded-lg border p-4 transition-shadow duration-150 hover:shadow-sm"
      style={{ borderColor: BORDER, background: "#fff" }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2 min-w-0">
          {job.status === "failed" ? (
            <AlertTriangle size={16} color={RED} className="mt-0.5 shrink-0" />
          ) : job.status === "processing" ? (
            <Loader2 size={16} color={BLUE} className="mt-0.5 shrink-0 animate-spin" />
          ) : (
            <FileText size={16} color={MUTED} className="mt-0.5 shrink-0" />
          )}
          <div className="min-w-0">
            <p
              className="text-sm font-medium truncate"
              style={{ color: job.status === "failed" ? RED : TEXT }}
            >
              {job.name}
            </p>
            <p className="text-[11px]" style={{ color: MUTED }}>
              {job.meta}
            </p>
          </div>
        </div>
        <StatusBadge status={job.status} />
      </div>

      {job.status === "failed" ? (
        <>
          <p
            className="text-xs mt-2 rounded-md px-3 py-2"
            style={{ background: "#FDEAE7", color: RED }}
          >
            <span className="font-semibold">Error: </span>
            {job.error}
          </p>
          <div className="flex items-center gap-4 mt-2">
            <button
              onClick={() => onRetry(job.id)}
              className="flex items-center gap-1 text-xs font-semibold hover:opacity-80"
              style={{ color: NAVY }}
            >
              <RotateCcw size={12} /> Retry Job
            </button>
            <button
              onClick={() => onIgnore(job.id)}
              className="flex items-center gap-1 text-xs font-semibold hover:opacity-80"
              style={{ color: MUTED }}
            >
              <X size={12} /> Ignore
            </button>
          </div>
        </>
      ) : (
        <StageDots stageIndex={job.stageIndex} status={job.status} />
      )}
    </div>
  );
}