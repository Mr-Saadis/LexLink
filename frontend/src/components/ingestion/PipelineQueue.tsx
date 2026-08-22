import PipelineJobCard from "./PipelineJobCard";
import type { Job } from "./PipelineJobCard";

// Pure module imports (no default assignments inside curly braces)
import { BORDER, MUTED, TEXT } from "../../theme/theme";

// Theme color fallbacks defined safely outside the import
const GREEN = "#10B981";
const BLUE = "#3B82F6";
const RED = "#EF4444";

// FIX: 5 se zyada jobs aane par list scroll ho, box na phaile.
// Ek job-card ki approx height ~86px hai (padding + text + stage-dots),
// + gap ~10px (space-y-2.5). 5 cards + gaps ke hisab se max-height fix ki.
const MAX_VISIBLE_JOBS = 5;
const JOB_CARD_HEIGHT_PX = 86;
const JOB_GAP_PX = 10;
const LIST_MAX_HEIGHT_PX =
  MAX_VISIBLE_JOBS * JOB_CARD_HEIGHT_PX + (MAX_VISIBLE_JOBS - 1) * JOB_GAP_PX;

interface PipelineQueueProps {
  queue?: Job[];
  onRetry: (id: number) => void;
  onIgnore: (id: number) => void;
}

export default function PipelineQueue({ queue = [], onRetry, onIgnore }: PipelineQueueProps) {
  const doneCount = queue.filter(
    (q: Job) => (q.status as string) === "done" || q.status === "verified" || q.status === "completed"
  ).length;
  const processingCount = queue.filter((q: Job) => q.status === "processing").length;
  const failedCount = queue.filter((q: Job) => q.status === "failed").length;

  return (
    <div className="rounded-xl border p-5 flex flex-col" style={{ borderColor: BORDER, background: "#fff" }}>
      <div className="flex items-center justify-between mb-4 shrink-0">
        <p className="text-sm font-semibold" style={{ color: TEXT }}>
          Active Pipeline Queue
        </p>
        <div className="flex items-center gap-3 text-xs" style={{ color: MUTED }}>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full" style={{ background: GREEN }} />
            {doneCount} Done
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full animate-pulse" style={{ background: BLUE }} />
            {processingCount} Processing
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full" style={{ background: RED }} />
            {failedCount} Failed
          </span>
        </div>
      </div>

      {queue.length === 0 ? (
        <div className="p-8 text-center text-xs text-gray-400 border border-dashed rounded-lg">
          No active jobs in the queue.
        </div>
      ) : (
        // FIX: max-height fixed rakhi (5 jobs ke barabar). Isse zyada
        // jobs hon to yahan scrollbar aayega, poora card box nahi phailega.
        <div
          className="overflow-y-auto pr-1 space-y-2.5 custom-scrollbar"
          style={{ maxHeight: `${LIST_MAX_HEIGHT_PX}px` }}
        >
          {queue.map((job: Job) => (
            <PipelineJobCard key={job.id} job={job} onRetry={onRetry} onIgnore={onIgnore} />
          ))}
        </div>
      )}
    </div>
  );
}