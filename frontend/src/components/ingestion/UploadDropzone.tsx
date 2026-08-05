import { useState, useRef } from "react";
import type { DragEvent, ChangeEvent } from "react";
import { UploadCloud } from "lucide-react";
import { BORDER, MUTED, TEXT, NAVY, GREEN } from "../../theme/theme";

interface UploadDropzoneProps {
  onFilesSelected: (files: File[]) => void;
}

export default function UploadDropzone({ onFilesSelected }: UploadDropzoneProps) {
  const [dragOver, setDragOver] = useState<boolean>(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    if (onFilesSelected && e.dataTransfer.files?.length) {
      onFilesSelected(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileInput = (e: ChangeEvent<HTMLInputElement>) => {
    if (onFilesSelected && e.target.files?.length) {
      onFilesSelected(Array.from(e.target.files));
    }
  };

  return (
    <div
      className="rounded-xl border p-6 flex flex-col items-center justify-center text-center"
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
        className="rounded-full flex items-center justify-center mb-3"
        style={{ width: 52, height: 52, background: "#EEF2F6" }}
      >
        <UploadCloud size={24} color={NAVY} />
      </div>
      <p className="text-sm font-medium" style={{ color: TEXT }}>
        Drag and drop legal PDFs here
      </p>
      <p className="text-xs mt-1" style={{ color: MUTED }}>
        Max file size: 50MB. Bulk upload supported.
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
        className="mt-4 px-5 py-2 rounded-lg text-sm font-semibold border"
        style={{ borderColor: BORDER, color: TEXT }}
      >
        Select Files
      </button>
    </div>
  );
}