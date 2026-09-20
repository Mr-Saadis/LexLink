import React, { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { X, Lock, Mail, Shield, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { NAVY, GREEN, BORDER, TEXT, MUTED, BG } from "../../theme/theme";

export default function AdminLoginModal() {
  const { isAuthModalOpen, setIsAuthModalOpen, login, error, isLoading, user, logout } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  if (!isAuthModalOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;
    await login(email, password);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
      <div
        className="w-full max-w-md rounded-2xl shadow-2xl border overflow-hidden bg-white"
        style={{ borderColor: BORDER }}
      >
        {/* Header */}
        <div className="px-6 py-5 text-white flex items-center justify-between" style={{ background: NAVY }}>
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center"
              style={{ background: GREEN }}
            >
              <Shield size={18} color="#fff" />
            </div>
            <div>
              <h2 className="text-base font-semibold font-serif tracking-wide">LexLink Admin Portal</h2>
              <p className="text-xs text-emerald-200/80">JWT Authentication & Role Control</p>
            </div>
          </div>
          <button
            onClick={() => setIsAuthModalOpen(false)}
            className="p-1.5 rounded-lg hover:bg-white/10 text-emerald-200 hover:text-white transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {user ? (
            /* Logged-In State */
            <div className="text-center py-4">
              <div
                className="w-14 h-14 mx-auto rounded-full flex items-center justify-center mb-3"
                style={{ background: BG }}
              >
                <CheckCircle2 size={28} color={GREEN} />
              </div>
              <h3 className="text-sm font-semibold" style={{ color: TEXT }}>
                Authenticated as Admin
              </h3>
              <p className="text-xs mt-1 font-mono text-emerald-800 bg-emerald-50 py-1 px-3 rounded-md inline-block border border-emerald-200">
                {user.email}
              </p>
              <p className="text-[11px] text-slate-500 mt-2">
                All document uploads will automatically be linked to your User ID in Supabase.
              </p>

              <div className="mt-6 flex gap-3">
                <button
                  type="button"
                  onClick={() => setIsAuthModalOpen(false)}
                  className="flex-1 py-2.5 rounded-xl text-xs font-semibold text-white shadow-sm transition-all"
                  style={{ background: NAVY }}
                >
                  Close
                </button>
                <button
                  type="button"
                  onClick={logout}
                  className="px-4 py-2.5 rounded-xl text-xs font-semibold border border-red-200 text-red-600 hover:bg-red-50 transition-colors"
                >
                  Sign Out
                </button>
              </div>
            </div>
          ) : (
            /* Login Form */
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="flex items-start gap-2 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs">
                  <AlertCircle size={16} className="shrink-0 mt-0.5 text-red-500" />
                  <span>{error}</span>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider mb-1.5" style={{ color: MUTED }}>
                  Admin Email
                </label>
                <div
                  className="flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl border bg-slate-50/50 focus-within:bg-white focus-within:ring-2 focus-within:ring-emerald-500/20 focus-within:border-emerald-500 transition-all"
                  style={{ borderColor: BORDER }}
                >
                  <Mail size={16} color={MUTED} />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="admin@lexlink.pk"
                    className="bg-transparent outline-none text-xs flex-1 text-slate-800 placeholder:text-slate-400"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider mb-1.5" style={{ color: MUTED }}>
                  Password
                </label>
                <div
                  className="flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl border bg-slate-50/50 focus-within:bg-white focus-within:ring-2 focus-within:ring-emerald-500/20 focus-within:border-emerald-500 transition-all"
                  style={{ borderColor: BORDER }}
                >
                  <Lock size={16} color={MUTED} />
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="bg-transparent outline-none text-xs flex-1 text-slate-800 placeholder:text-slate-400"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full mt-2 py-3 rounded-xl text-xs font-semibold text-white flex items-center justify-center gap-2 shadow-md hover:brightness-105 active:scale-[0.99] disabled:opacity-60 transition-all"
                style={{ background: NAVY }}
              >
                {isLoading ? (
                  <>
                    <Loader2 size={15} className="animate-spin" />
                    Authenticating with Supabase...
                  </>
                ) : (
                  <>
                    <Lock size={14} />
                    Sign In to Console
                  </>
                )}
              </button>

              <div className="pt-2 text-center">
                <p className="text-[11px] text-slate-400">
                  Secured by Supabase JWT & Role-Based Access
                </p>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
