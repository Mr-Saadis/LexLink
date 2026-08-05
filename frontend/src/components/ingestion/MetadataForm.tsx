import { ChevronDown } from "lucide-react";
import { BORDER, MUTED, TEXT, GREEN, GREEN_DARK } from "../../theme/theme";

type DocType = "judgment" | "statute";

interface MetadataFormProps {
  courtType: string;
  onCourtTypeChange: (value: string) => void;
  docType: DocType;
  onDocTypeChange: (value: DocType) => void;
  titleTemplate: string;
  onTitleTemplateChange: (value: string) => void;
}

export default function MetadataForm({
  courtType,
  onCourtTypeChange,
  docType,
  onDocTypeChange,
  titleTemplate,
  onTitleTemplateChange,
}: MetadataFormProps) {
  const docTypeOptions: DocType[] = ["judgment", "statute"];

  return (
    <div className="rounded-xl border p-5" style={{ borderColor: BORDER, background: "#fff" }}>
      <p className="text-sm font-semibold mb-4" style={{ color: TEXT }}>
        Batch Metadata Override
      </p>

      <label className="text-xs font-medium" style={{ color: MUTED }}>
        Court Type
      </label>
      <div className="relative mt-1 mb-4">
        <select
          value={courtType}
          onChange={(e) => onCourtTypeChange(e.target.value)}
          className="w-full appearance-none px-3 py-2 rounded-lg border text-sm outline-none"
          style={{ borderColor: BORDER, color: TEXT, background: "#fff" }}
        >
          <option>Supreme Court (SC)</option>
          <option>Lahore High Court (LHC)</option>
          <option>Statute</option>
        </select>
        <ChevronDown
          size={15}
          color={MUTED}
          className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none"
        />
      </div>

      <label className="text-xs font-medium" style={{ color: MUTED }}>
        Document Type
      </label>
      <div className="flex items-center gap-3 mt-2 mb-4">
        {docTypeOptions.map((type) => (
          <button
            key={type}
            onClick={() => onDocTypeChange(type)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-full border text-sm font-medium"
            style={{
              borderColor: docType === type ? GREEN : BORDER,
              background: docType === type ? "#E7F6EC" : "#fff",
              color: docType === type ? GREEN_DARK : MUTED,
            }}
          >
            <span
              className="rounded-full"
              style={{
                width: 8,
                height: 8,
                background: docType === type ? GREEN : BORDER,
              }}
            />
            {type === "judgment" ? "Judgment" : "Statute"}
          </button>
        ))}
      </div>

      <label className="text-xs font-medium" style={{ color: MUTED }}>
        Title Template Override
      </label>
      <input
        value={titleTemplate}
        onChange={(e) => onTitleTemplateChange(e.target.value)}
        placeholder="e.g. {Court}_{Year}_{ID}"
        className="w-full mt-1 px-3 py-2 rounded-lg border text-sm outline-none"
        style={{ borderColor: BORDER, color: TEXT }}
      />
    </div>
  );
}