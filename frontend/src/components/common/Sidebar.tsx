import {
  LayoutDashboard,
  FileInput,
  ClipboardCheck,
  Library,
  ScrollText,
  BarChart3,
  ShieldCheck,
  HelpCircle,
} from "lucide-react";
import type { ComponentType } from "react";
import type { LucideProps } from "lucide-react";
import { NAVY, NAVY_LIGHT, GREEN } from "../../theme/theme";

interface NavItem {
  icon: ComponentType<LucideProps>;
  label: string;
}

const navItems: NavItem[] = [
  { icon: LayoutDashboard, label: "Dashboard" },
  { icon: FileInput, label: "Document Ingestion" },
  { icon: ClipboardCheck, label: "Verification Queue" },
  { icon: Library, label: "Document Library" },
  { icon: ScrollText, label: "Pipeline Logs" },
  { icon: BarChart3, label: "Usage Analytics" },
];

interface SidebarProps {
  activeLabel?: string;
  onNavigate?: (label: string) => void;
}

export default function Sidebar({ activeLabel = "Document Ingestion", onNavigate }: SidebarProps) {
  return (
    <aside
      className="hidden md:flex flex-col justify-between shrink-0"
      style={{ width: 232, background: NAVY }}
    >
      <div>
        <div className="flex items-center gap-2 px-5 py-6">
          <div
            className="rounded-md flex items-center justify-center"
            style={{ width: 30, height: 30, background: GREEN }}
          >
            <ScrollText size={16} color="#fff" />
          </div>
          <div>
            <p className="text-white font-semibold text-sm leading-none">LexLink</p>
            <p className="text-[10px] tracking-wide" style={{ color: "#7C93AC" }}>
              Admin Console
            </p>
          </div>
        </div>

        <nav className="px-3 mt-2 flex flex-col gap-1">
          {navItems.map(({ icon: Icon, label }) => {
            const active = label === activeLabel;
            return (
              <button
                key={label}
                onClick={() => onNavigate && onNavigate(label)}
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors"
                style={{
                  background: active ? GREEN : "transparent",
                  color: active ? "#fff" : "#B7C4D4",
                }}
              >
                <Icon size={16} />
                <span className="text-[13px] font-medium">{label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      <div className="px-3 pb-5 flex flex-col gap-1">
        <div className="h-px mx-2 mb-2" style={{ background: NAVY_LIGHT }} />
        <button
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-left"
          style={{ color: "#B7C4D4" }}
        >
          <ShieldCheck size={16} />
          <span className="text-[13px] font-medium">System Status</span>
        </button>
        <button
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-left"
          style={{ color: "#B7C4D4" }}
        >
          <HelpCircle size={16} />
          <span className="text-[13px] font-medium">Help</span>
        </button>
      </div>
    </aside>
  );
}