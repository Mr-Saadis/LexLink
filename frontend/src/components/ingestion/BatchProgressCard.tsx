import { Play } from "lucide-react";
import { BORDER, MUTED, TEXT, GREEN } from "../../theme/theme";

interface BatchProgressCardProps {
  doneCount: number;
  totalCount: number;
  onResume: () => void;
}

export default function BatchProgressCard({ doneCount, totalCount, onResume }: BatchProgressCardProps) {
  const pct = totalCount > 0 ? (doneCount / totalCount) * 100 : 0;

  return (
    <div
      className="rounded-xl border flex items-center gap-5 px-5 py-3"
      style={{ borderColor: BORDER, background: "#fff" }}
    >
      <div>
        <p className="text-[11px] font-semibold" style={{ color: MUTED }}>
          Batch Progress
        </p>
        <div className="flex items-center gap-2 mt-1">
          <div className="rounded-full h-1.5 w-24 overflow-hidden" style={{ background: BORDER }}>
            <div
              className="h-1.5 rounded-full transition-all duration-300 ease-out"
              style={{ width: `${pct}%`, background: GREEN }}
            />
          </div>
          <span className="text-xs" style={{ color: TEXT }}>
            {doneCount}/{totalCount} Files Processed
          </span>
        </div>
      </div>
      <button
        onClick={onResume}
        className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white transition-transform duration-150 hover:opacity-90 active:scale-[0.98]"
        style={{ background: GREEN }}
      >
        <Play size={14} fill="#fff" /> Resume Batch
      </button>
    </div>
  );
}
