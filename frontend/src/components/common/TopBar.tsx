import { Search, Bell, User } from "lucide-react";
import { BORDER, MUTED, TEXT, BG, NAVY } from "../../theme/theme";
import { useAuth } from "../../context/AuthContext";

interface TopBarProps {
  searchValue: string;
  onSearchChange: (value: string) => void;
  userInitials?: string;
  onNavigateToAuth?: () => void;
}

export default function TopBar({
  searchValue,
  onSearchChange,
  userInitials = "AK",
  onNavigateToAuth,
}: TopBarProps) {
  const { user, isAuthenticated } = useAuth();

  const initials = user?.email
    ? user.email.slice(0, 2).toUpperCase()
    : userInitials;

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

        {isAuthenticated && user ? (
          <button
            onClick={() => onNavigateToAuth && onNavigateToAuth()}
            title={`Logged in as ${user.name || user.email} (${user.role || "User"}) - Click to manage account`}
            className="relative rounded-full flex items-center justify-center font-semibold transition-all hover:scale-105 active:scale-95 shadow-sm border border-emerald-300"
            style={{ width: 34, height: 34, background: "#D1FAE5", color: NAVY }}
          >
            <span className="text-xs">{initials}</span>
            <span className="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full bg-emerald-500 border-2 border-white ring-1 ring-emerald-600/30"></span>
          </button>
        ) : (
          <button
            onClick={() => onNavigateToAuth && onNavigateToAuth()}
            title="Sign In / Register"
            className="rounded-full flex items-center justify-center transition-all hover:scale-105 active:scale-95 shadow-sm border border-slate-200 bg-slate-100 hover:bg-slate-200 text-slate-700 hover:text-slate-900"
            style={{ width: 34, height: 34 }}
          >
            <User className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}