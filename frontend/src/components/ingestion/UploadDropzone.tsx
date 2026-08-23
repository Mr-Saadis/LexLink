import { useState, useRef } from "react";
import type { DragEvent, ChangeEvent } from "react";
import { UploadCloud, Building2, Scale } from "lucide-react";
import { BORDER, MUTED, TEXT, NAVY, GREEN } from "../../theme/theme";

interface UploadDropzoneProps {
  onFilesSelected: (files: File[], courtType: "SC" | "HC") => void;
}

export default function UploadDropzone({ onFilesSelected }: UploadDropzoneProps) {
  const [dragOver, setDragOver] = useState<boolean>(false);
  const [courtType, setCourtType] = useState<"SC" | "HC">("SC");
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    if (onFilesSelected && e.dataTransfer.files?.length) {
      onFilesSelected(Array.from(e.dataTransfer.files), courtType);
    }
  };

  const handleFileInput = (e: ChangeEvent<HTMLInputElement>) => {
    if (onFilesSelected && e.target.files?.length) {
      onFilesSelected(Array.from(e.target.files), courtType);
    }
    e.target.value = "";
  };

  return (
    <div className="h-full flex flex-col gap-3">
      {/* Court Type Selection Field */}
      <div className="bg-white rounded-xl border p-3 flex flex-col sm:flex-row items-center justify-between gap-2 shadow-xs" style={{ borderColor: BORDER }}>
        <div className="flex items-center gap-2">
          <Scale size={16} className="text-emerald-700" />
          <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: TEXT }}>
            Declared Court Type:
          </span>
        </div>
        <div className="flex items-center gap-1.5 w-full sm:w-auto">
          <button
            type="button"
            onClick={() => setCourtType("SC")}
            className={`flex-1 sm:flex-initial flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              courtType === "SC"
                ? "bg-emerald-800 text-white shadow-xs"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            <Building2 size={13} />
            Supreme Court (SC)
          </button>
          <button
            type="button"
            onClick={() => setCourtType("HC")}
            className={`flex-1 sm:flex-initial flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              courtType === "HC"
                ? "bg-emerald-800 text-white shadow-xs"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            <Scale size={13} />
            High Court (HC)
          </button>
        </div>
      </div>

      {/* Dropzone Area */}
      <div
        className="flex-1 rounded-xl border p-6 flex flex-col items-center justify-center text-center transition-colors duration-150"
        style={{
          borderColor: dragOver ? GREEN : BORDER,
          borderStyle: "dashed",
          background: dragOver ? "#EFFBF3" : "#fff",
        }}
        onDragOver={(e: DragEvent<HTMLDivElement>) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
      >
        <div
          className="rounded-full flex items-center justify-center mb-3 transition-transform duration-150"
          style={{
            width: 52,
            height: 52,
            background: "#EEF2F6",
            transform: dragOver ? "scale(1.08)" : "scale(1)",
          }}
        >
          <UploadCloud size={24} color={NAVY} />
        </div>
        <p className="text-sm font-medium" style={{ color: TEXT }}>
          Drag and drop legal PDFs here
        </p>
        <p className="text-xs mt-1" style={{ color: MUTED }}>
          Batch upload enabled • Tagged as <span className="font-semibold text-emerald-800">[{courtType}]</span>
        </p>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          multiple
          className="hidden"
          onChange={handleFileInput}
        />
        <button
          onClick={() => inputRef.current?.click()}
          className="mt-4 px-5 py-2 rounded-lg text-sm font-semibold border transition-colors duration-150 hover:bg-gray-50 active:scale-[0.98]"
          style={{ borderColor: BORDER, color: TEXT }}
        >
          Select Files ({courtType})
        </button>
      </div>
    </div>
  );
}