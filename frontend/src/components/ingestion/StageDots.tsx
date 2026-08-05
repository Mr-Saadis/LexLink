import { Loader2 } from "lucide-react";
// Import type separately for JobStatus
import type { JobStatus } from "../../theme/theme";
import { STAGES, GREEN, GREEN_DARK, BLUE, RED, BORDER, MUTED } from "../../theme/theme";

interface StageDotsProps {
  stageIndex: number;
  status: JobStatus;
}

export default function StageDots({ stageIndex, status }: StageDotsProps) {
  return (
    <div className="flex items-center gap-1.5 mt-3">
      {STAGES.map((stage: string, i: number) => {
        const done = i < stageIndex;
        const current = i === stageIndex && status === "processing";
        const failed = i === stageIndex && status === "failed";
        return (
          <div key={stage} className="flex flex-col items-center gap-1" style={{ width: 56 }}>
            <div className="flex items-center w-full">
              {i !== 0 && (
                <div
                  className="h-[2px] flex-1"
                  style={{ background: done || current ? GREEN : BORDER }}
                />
              )}
              <div
                className="rounded-full flex items-center justify-center shrink-0"
                style={{
                  width: 16,
                  height: 16,
                  background: failed ? RED : done ? GREEN : current ? BLUE : "#fff",
                  border: `2px solid ${
                    failed ? RED : done ? GREEN : current ? BLUE : BORDER
                  }`,
                }}
              >
                {current && <Loader2 size={10} className="animate-spin" color="#fff" />}
              </div>
              {i !== STAGES.length - 1 && (
                <div
                  className="h-[2px] flex-1"
                  style={{ background: done ? GREEN : BORDER }}
                />
              )}
            </div>
            <span
              className="text-[9px] text-center leading-tight"
              style={{ color: current ? BLUE : done ? GREEN_DARK : MUTED }}
            >
              {stage}
            </span>
          </div>
        );
      })}
    </div>
  );
}