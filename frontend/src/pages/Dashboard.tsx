import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import {
  FileText,
  Database,
  CheckCircle2,
  Shield,
  Layers,
  ArrowUpRight,
  Clock,
  Sparkles,
  Server,
  Activity,
} from "lucide-react";
import { NAVY, GREEN, BORDER, TEXT, MUTED, BG } from "../theme/theme";

interface DashboardProps {
  onNavigateToIngestion?: () => void;
}

interface SystemStats {
  status: string;
  documents_count: number;
  chunks_count: number;
  qdrant_points_count: number;
  qdrant_status: string;
  qdrant_connected: boolean;
  supabase_connected: boolean;
  cloudflare_r2_connected: boolean;
  vector_dimension: number;
  embedding_model: string;
  recent_documents: Array<{
    id: string;
    title: string;
    court_type?: string;
    total_chunks?: number;
    created_at?: string;
    source_file?: string;
  }>;
}

export default function Dashboard({ onNavigateToIngestion }: DashboardProps) {
  const { user } = useAuth();
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Admin creation state
  const [isAddAdminOpen, setIsAddAdminOpen] = useState<boolean>(false);
  const [adminName, setAdminName] = useState<string>("");
  const [adminEmail, setAdminEmail] = useState<string>("");
  const [adminPassword, setAdminPassword] = useState<string>("");
  const [adminCreating, setAdminCreating] = useState<boolean>(false);
  const [adminMessage, setAdminMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const fetchStats = async () => {
    try {
      const token = localStorage.getItem("token") || localStorage.getItem("access_token");
      const headers: Record<string, string> = {};
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
      const res = await fetch("http://localhost:8000/api/stats", { headers });
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (err) {
      console.error("Failed to load dashboard metrics:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const handleCreateAdmin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAdminCreating(true);
    setAdminMessage(null);
    try {
      const token = localStorage.getItem("token") || localStorage.getItem("access_token");
      const res = await fetch("http://localhost:8000/api/auth/admin/create-admin", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: adminName,
          email: adminEmail,
          password: adminPassword,
          role: "admin",
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to create administrator.");
      }

      setAdminMessage({ type: "success", text: `Admin '${adminEmail}' provisioned successfully!` });
      setAdminName("");
      setAdminEmail("");
      setAdminPassword("");
    } catch (err: any) {
      setAdminMessage({ type: "error", text: err.message || "Failed to provision administrator." });
    } finally {
      setAdminCreating(false);
    }
  };

  const docCount = stats?.documents_count ?? 0;
  const chunkCount = stats?.chunks_count ?? 0;
  const vectorPoints = stats?.qdrant_points_count ?? 0;
  const r2Connected = stats?.cloudflare_r2_connected ?? false;
  const qdrantConnected = stats?.qdrant_connected ?? false;
  const supabaseConnected = stats?.supabase_connected ?? false;
  const isAdmin = user?.role === "admin";

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col gap-6">
      {/* Welcome Banner */}
      <div
        className="rounded-2xl p-6 text-white flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-lg"
        style={{ background: `linear-gradient(135deg, ${NAVY} 0%, #065F46 100%)` }}
      >
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-200 text-xs font-semibold mb-2 border border-emerald-400/30">
            <Shield size={13} />
            <span>Admin Control Center</span>
          </div>
          <h1 className="text-2xl font-bold font-serif">
            Welcome back, {user?.name || "Admin"}
          </h1>
          <p className="text-xs text-emerald-100/80 mt-1">
            LexLink Supreme Court & High Court Intelligence Pipeline is active and operational.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {isAdmin && (
            <button
              onClick={() => {
                setAdminMessage(null);
                setIsAddAdminOpen(true);
              }}
              className="px-4 py-2.5 rounded-xl text-xs font-semibold text-white bg-emerald-800/80 hover:bg-emerald-700/80 transition-all border border-emerald-500/30 flex items-center gap-2 shadow-sm active:scale-95"
            >
              <Shield size={14} />
              <span>+ Add Admin</span>
            </button>
          )}

          <button
            onClick={onNavigateToIngestion}
            className="px-5 py-2.5 rounded-xl text-xs font-semibold text-slate-900 bg-emerald-300 hover:bg-emerald-200 transition-all shadow-md flex items-center gap-2 active:scale-95 shrink-0"
          >
            <FileText size={15} />
            <span>Upload Judgments</span>
            <ArrowUpRight size={14} />
          </button>
        </div>
      </div>

      {/* Add Admin Modal */}
      {isAddAdminOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="w-full max-w-md bg-white rounded-2xl border shadow-2xl overflow-hidden" style={{ borderColor: BORDER }}>
            <div className="px-6 py-4 flex items-center justify-between text-white" style={{ background: NAVY }}>
              <div className="flex items-center gap-2">
                <Shield size={16} className="text-emerald-400" />
                <h3 className="text-sm font-semibold">Provision New Administrator</h3>
              </div>
              <button
                onClick={() => setIsAddAdminOpen(false)}
                className="text-emerald-200 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateAdmin} className="p-6 space-y-4">
              {adminMessage && (
                <div className={`p-3 rounded-xl text-xs border ${adminMessage.type === "success" ? "bg-emerald-50 border-emerald-200 text-emerald-800" : "bg-red-50 border-red-200 text-red-800"}`}>
                  {adminMessage.text}
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: MUTED }}>
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Co-Admin Name"
                  value={adminName}
                  onChange={(e) => setAdminName(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl border bg-slate-50 text-xs focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                  style={{ borderColor: BORDER }}
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: MUTED }}>
                  Admin Email
                </label>
                <input
                  type="email"
                  required
                  placeholder="newadmin@lexlink.pk"
                  value={adminEmail}
                  onChange={(e) => setAdminEmail(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl border bg-slate-50 text-xs focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                  style={{ borderColor: BORDER }}
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: MUTED }}>
                  Password
                </label>
                <input
                  type="password"
                  required
                  placeholder="••••••••••••"
                  value={adminPassword}
                  onChange={(e) => setAdminPassword(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl border bg-slate-50 text-xs focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                  style={{ borderColor: BORDER }}
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsAddAdminOpen(false)}
                  className="flex-1 py-2.5 rounded-xl border text-xs font-semibold text-slate-600 hover:bg-slate-50"
                  style={{ borderColor: BORDER }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={adminCreating}
                  className="flex-1 py-2.5 rounded-xl text-xs font-semibold text-white shadow-sm flex items-center justify-center gap-2"
                  style={{ background: NAVY }}
                >
                  {adminCreating ? "Provisioning..." : "Create Admin Account"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Real Live Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            title: "Ingested Documents",
            value: isLoading ? "..." : `${docCount}`,
            desc: "Persisted in Supabase",
            icon: FileText,
            color: GREEN,
          },
          {
            title: "Supabase Chunks",
            value: isLoading ? "..." : `${chunkCount}`,
            desc: "Indexed with Bounding Boxes",
            icon: Layers,
            color: "#3B82F6",
          },
          {
            title: "Qdrant Vector Points",
            value: isLoading ? "..." : `${vectorPoints}`,
            desc: `${stats?.embedding_model || "BAAI/bge-m3"} (1024-dim)`,
            icon: Sparkles,
            color: "#8B5CF6",
          },
          {
            title: "Storage & Cloud Status",
            value: r2Connected && supabaseConnected ? "Active" : "Operational",
            desc: `R2: ${r2Connected ? "Online" : "Pending"} • Qdrant: ${qdrantConnected ? "Online" : "Local"}`,
            icon: Database,
            color: "#F59E0B",
          },
        ].map((stat, idx) => {
          const Icon = stat.icon;
          return (
            <div
              key={idx}
              className="bg-white rounded-2xl p-5 border shadow-sm flex flex-col justify-between"
              style={{ borderColor: BORDER }}
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: MUTED }}>
                  {stat.title}
                </span>
                <div
                  className="w-9 h-9 rounded-xl flex items-center justify-center"
                  style={{ background: BG }}
                >
                  <Icon size={18} color={stat.color} />
                </div>
              </div>
              <div>
                <p className="text-2xl font-bold font-serif" style={{ color: TEXT }}>
                  {stat.value}
                </p>
                <div className="flex items-center gap-1.5 mt-1.5 text-[11px] text-slate-500">
                  <CheckCircle2 size={12} className="text-emerald-600" />
                  <span>{stat.desc}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Recent Activity & System Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div
          className="lg:col-span-2 bg-white rounded-2xl p-6 border shadow-sm"
          style={{ borderColor: BORDER }}
        >
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Activity size={18} className="text-emerald-600" />
              <h2 className="text-base font-semibold" style={{ color: TEXT }}>
                Recent Ingested Judgments
              </h2>
            </div>
            <span className="text-xs text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full font-medium border border-emerald-200">
              Live Database
            </span>
          </div>

          <div className="space-y-3">
            {isLoading ? (
              <div className="text-center py-8 text-xs text-slate-400">Loading recent documents...</div>
            ) : stats?.recent_documents && stats.recent_documents.length > 0 ? (
              stats.recent_documents.map((doc, i) => (
                <div
                  key={doc.id || i}
                  className="flex items-center justify-between p-3.5 rounded-xl border bg-slate-50/50 hover:bg-slate-50 transition-colors"
                  style={{ borderColor: BORDER }}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-emerald-100 flex items-center justify-center text-emerald-800 font-bold text-xs">
                      {doc.declared_court_type || doc.court_type || "SC"}
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-slate-800 line-clamp-1">
                        {doc.title || doc.source_file || "Judgment Record"}
                      </p>
                      <p className="text-[11px] text-slate-500">
                        {doc.total_chunks ? `${doc.total_chunks} Chunks` : "Parsed"} • {doc.source_file || "PDF Source"}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 text-[11px] text-slate-500 font-medium shrink-0">
                    <Clock size={12} className="text-emerald-600" />
                    <span>{doc.created_at ? new Date(doc.created_at).toLocaleDateString() : "Active"}</span>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-xs text-slate-500 bg-slate-50/50 rounded-xl border border-dashed border-slate-200">
                <p>No documents ingested yet.</p>
                <button
                  onClick={onNavigateToIngestion}
                  className="mt-2 text-emerald-700 hover:underline font-semibold"
                >
                  Upload your first judgment PDF
                </button>
              </div>
            )}
          </div>
        </div>

        <div
          className="bg-white rounded-2xl p-6 border shadow-sm flex flex-col justify-between"
          style={{ borderColor: BORDER }}
        >
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Server size={18} className="text-emerald-700" />
              <h2 className="text-base font-semibold" style={{ color: TEXT }}>
                System & Session Info
              </h2>
            </div>
            <p className="text-xs text-slate-500 mb-4">Current user credentials and infrastructure health</p>

            <div className="p-4 rounded-xl border bg-slate-50/50 space-y-2.5" style={{ borderColor: BORDER }}>
              <div className="flex justify-between text-xs">
                <span className="text-slate-500">User:</span>
                <span className="font-semibold text-slate-800">{user?.name || "Administrator"}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-500">Role:</span>
                <span className="font-semibold text-emerald-700 uppercase">{user?.role || "ADMIN"}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-500">Email:</span>
                <span className="font-mono text-slate-800">{user?.email || "admin@lexlink.pk"}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-500">Supabase DB:</span>
                <span className={`font-semibold ${supabaseConnected ? "text-emerald-600" : "text-amber-600"}`}>
                  {supabaseConnected ? "Connected" : "Not Configured"}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-500">Qdrant Vector DB:</span>
                <span className="font-semibold text-emerald-600">
                  {qdrantConnected ? "Docker/Cloud Active" : "Embedded Local Disk"}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-500">Cloudflare R2:</span>
                <span className={`font-semibold ${r2Connected ? "text-emerald-600" : "text-amber-600"}`}>
                  {r2Connected ? "Vault Connected" : "Local Disk"}
                </span>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t mt-4" style={{ borderColor: BORDER }}>
            <p className="text-[11px] text-slate-400 text-center">
              LexLink RBAC Security & BAAI/bge-m3 Semantic Vectors
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
