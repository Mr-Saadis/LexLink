import { CheckCircle2 } from "lucide-react";
import { BORDER, MUTED, GREEN } from "../../theme/theme";

export default function Footer() {
  return (
    <div
      className="flex items-center justify-between px-6 py-2.5 border-t text-[11px]"
      style={{ borderColor: BORDER, background: "#fff", color: MUTED }}
    >
      <span>LexLink Admin v2.4.0 • © 2024 Legal Infrastructure Group</span>
      <div className="flex items-center gap-4">
        <span className="flex items-center gap-1">
          <CheckCircle2 size={12} color={GREEN} /> Cloudflare: Healthy
        </span>
        <span className="flex items-center gap-1">
          <CheckCircle2 size={12} color={GREEN} /> Supabase: Operational
        </span>
        <span className="flex items-center gap-1">
          <CheckCircle2 size={12} color={GREEN} /> Qdrant Online
        </span>
      </div>
    </div>
  );
}