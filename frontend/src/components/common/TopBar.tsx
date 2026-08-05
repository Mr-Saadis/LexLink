import { Search, Bell } from "lucide-react";
import { BORDER, MUTED, TEXT, BG, NAVY } from "../../theme/theme";

interface TopBarProps {
  searchValue: string;
  onSearchChange: (value: string) => void;
  userInitials?: string;
}

export default function TopBar({ searchValue, onSearchChange, userInitials = "AK" }: TopBarProps) {
  return (
    <div
      className="flex items-center justify-between px-6 py-3 border-b"
      style={{ borderColor: BORDER, background: "#fff" }}
    >
      <div
        className="flex items-center gap-2 px-3 py-2 rounded-lg flex-1 max-w-md"
        style={{ background: BG }}
      >
        <Search size={15} color={MUTED} />
        <input
          value={searchValue}
          onChange={(e) => onSearchChange && onSearchChange(e.target.value)}
          placeholder="Search case ID or document name..."
          className="bg-transparent outline-none text-sm flex-1"
          style={{ color: TEXT }}
        />
      </div>
      <div className="flex items-center gap-4 ml-4">
        <Bell size={18} color={MUTED} />
        <div
          className="rounded-full flex items-center justify-center text-xs font-semibold"
          style={{ width: 30, height: 30, background: "#DCE7F5", color: NAVY }}
        >
          {userInitials}
        </div>
      </div>
    </div>
  );
}