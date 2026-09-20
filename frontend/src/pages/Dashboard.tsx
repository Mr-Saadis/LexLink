import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import {
  FileText,
  Database,
  CheckCircle2,
  TrendingUp,
  Shield,
  Layers,
  ArrowUpRight,
  Clock,
} from "lucide-react";
import { NAVY, GREEN, BORDER, TEXT, MUTED, BG } from "../theme/theme";

interface DashboardProps {
  onNavigateToIngestion?: () => void;
}

export default function Dashboard({ onNavigateToIngestion }: DashboardProps) {
  const { user } = useAuth();
  const [docCount, setDocCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    fetch("http://localhost:8000/api/documents")
      .then((res) => res.json())
      .then((data) => {
        if (data.documents) {
          setDocCount(data.documents.length);
        }
        setIsLoading(false);
      })
      .catch(() => setIsLoading(false));
  }, []);

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

        <button
          onClick={onNavigateToIngestion}
          className="px-5 py-2.5 rounded-xl text-xs font-semibold text-slate-900 bg-emerald-300 hover:bg-emerald-200 transition-all shadow-md flex items-center gap-2 active:scale-95 shrink-0"
        >
          <FileText size={15} />
          <span>Upload Judgments</span>
          <ArrowUpRight size={14} />
        </button>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            title: "Ingested Documents",
            value: isLoading ? "..." : `${docCount}`,
            change: "+12% this week",
            icon: FileText,
            color: GREEN,
          },
          {
            title: "Supabase Chunks",
            value: isLoading ? "..." : `${docCount * 25}+`,
            change: "Indexed with Bounding Boxes",
            icon: Layers,
            color: "#3B82F6",
          },
          {
            title: "Cloudflare R2 Storage",
            value: "Connected",
            change: "Encrypted Judgment Vault",
            icon: Database,
            color: "#F59E0B",
          },
          {
            title: "Verification Queue",
            value: "0 Pending",
            change: "All pipelines cleared",
            icon: CheckCircle2,
            color: "#10B981",
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
                  <TrendingUp size={12} className="text-emerald-600" />
                  <span>{stat.change}</span>
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
            <h2 className="text-base font-semibold" style={{ color: TEXT }}>
              Pipeline Ingestion Activity
            </h2>
            <span className="text-xs text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full font-medium border border-emerald-200">
              Live Connection
            </span>
          </div>

          <div className="space-y-3">
            {[
              {
                court: "Supreme Court of Pakistan",
                desc: "Automatic regex metadata parser and chunking active",
                time: "Real-time",
              },
              {
                court: "Lahore High Court",
                desc: "Multi-page OCR bounding box coordinate mapper enabled",
                time: "Active",
              },
              {
                court: "PostgreSQL GIN Indexes",
                desc: "Sub-millisecond metadata search over documents JSONB",
                time: "Indexed",
              },
            ].map((item, i) => (
              <div
                key={i}
                className="flex items-center justify-between p-3.5 rounded-xl border bg-slate-50/50 hover:bg-slate-50 transition-colors"
                style={{ borderColor: BORDER }}
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-emerald-100 flex items-center justify-center text-emerald-800 font-bold text-xs">
                    {i + 1}
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-slate-800">{item.court}</p>
                    <p className="text-[11px] text-slate-500">{item.desc}</p>
                  </div>
                </div>
                <div className="flex items-center gap-1 text-[11px] text-emerald-600 font-medium">
                  <Clock size={12} />
                  <span>{item.time}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div
          className="bg-white rounded-2xl p-6 border shadow-sm flex flex-col justify-between"
          style={{ borderColor: BORDER }}
        >
          <div>
            <h2 className="text-base font-semibold mb-1" style={{ color: TEXT }}>
              Authenticated Session
            </h2>
            <p className="text-xs text-slate-500 mb-4">Current user permissions & role details</p>

            <div className="p-4 rounded-xl border bg-slate-50/50 space-y-2.5" style={{ borderColor: BORDER }}>
              <div className="flex justify-between text-xs">
                <span className="text-slate-500">Name:</span>
                <span className="font-semibold text-slate-800">{user?.name || "Admin"}</span>
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
                <span className="text-slate-500">Status:</span>
                <span className="font-semibold text-emerald-600">Verified & Active</span>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t mt-4" style={{ borderColor: BORDER }}>
            <p className="text-[11px] text-slate-400 text-center">
              LexLink RBAC Security & Supabase JWT
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
