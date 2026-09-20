import React, { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import {
  X,
  Lock,
  Mail,
  User as UserIcon,
  Shield,
  Briefcase,
  Scale,
  CreditCard,
  FileBadge,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { NAVY, GREEN, BORDER, TEXT, MUTED, BG } from "../../theme/theme";

interface AuthModalProps {
  onAdminLogin?: () => void;
}

export default function AuthModal({ onAdminLogin }: AuthModalProps) {
  const { isAuthModalOpen, setIsAuthModalOpen, login, signup, error, isLoading, user, logout } = useAuth();
  
  const [tab, setTab] = useState<"login" | "signup">("login");
  const [role, setRole] = useState<"layman" | "lawyer">("layman");

  // Form states
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [licenseNo, setLicenseNo] = useState("");
  const [cnic, setCnic] = useState("");

  if (!isAuthModalOpen) return null;

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;
    const loggedUser = await login(email, password);
    if (loggedUser && (loggedUser.role === "admin" || email.toLowerCase().includes("admin"))) {
      if (onAdminLogin) onAdminLogin();
    }
  };

  const handleSignupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password || !name) return;

    await signup({
      email,
      password,
      name,
      role,
      license_no: role === "lawyer" ? licenseNo : undefined,
      cnic: role === "lawyer" ? cnic : undefined,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/55 backdrop-blur-sm animate-in fade-in duration-200">
      <div
        className="w-full max-w-lg rounded-2xl shadow-2xl border overflow-hidden bg-white max-h-[90vh] flex flex-col"
        style={{ borderColor: BORDER }}
      >
        {/* Header */}
        <div className="px-6 py-4 text-white flex items-center justify-between shrink-0" style={{ background: NAVY }}>
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center"
              style={{ background: GREEN }}
            >
              <Scale size={18} color="#fff" />
            </div>
            <div>
              <h2 className="text-base font-semibold font-serif tracking-wide">LexLink Authentication</h2>
              <p className="text-[11px] text-emerald-200/80">
                Unified Legal Intelligence & Research Portal
              </p>
            </div>
          </div>
          <button
            onClick={() => setIsAuthModalOpen(false)}
            className="p-1.5 rounded-lg hover:bg-white/10 text-emerald-200 hover:text-white transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex-1">
          {user ? (
            /* Logged-In User Profile Screen */
            <div className="text-center py-4">
              <div
                className="w-16 h-16 mx-auto rounded-full flex items-center justify-center mb-3 shadow-inner"
                style={{ background: BG }}
              >
                <CheckCircle2 size={32} color={GREEN} />
              </div>
              <h3 className="text-base font-semibold" style={{ color: TEXT }}>
                {user.name || "Authenticated User"}
              </h3>
              <p className="text-xs text-slate-500 font-mono mt-0.5">{user.email}</p>
              
              <div className="mt-3 inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">
                <Shield size={13} />
                <span>Role: {user.role?.toUpperCase() || "USER"}</span>
                {user.verification_status && (
                  <span className="text-[10px] opacity-75 font-normal">({user.verification_status})</span>
                )}
              </div>

              <div className="mt-6 flex gap-3 max-w-xs mx-auto">
                <button
                  type="button"
                  onClick={() => setIsAuthModalOpen(false)}
                  className="flex-1 py-2.5 rounded-xl text-xs font-semibold text-white shadow-sm transition-all hover:brightness-105"
                  style={{ background: NAVY }}
                >
                  Continue
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
            /* Login / Signup Form */
            <div>
              {/* Tab Switcher */}
              <div className="flex rounded-xl p-1 bg-slate-100 mb-5">
                <button
                  type="button"
                  onClick={() => setTab("login")}
                  className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all ${
                    tab === "login"
                      ? "bg-white text-slate-900 shadow-sm"
                      : "text-slate-500 hover:text-slate-800"
                  }`}
                >
                  Sign In
                </button>
                <button
                  type="button"
                  onClick={() => setTab("signup")}
                  className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all ${
                    tab === "signup"
                      ? "bg-white text-slate-900 shadow-sm"
                      : "text-slate-500 hover:text-slate-800"
                  }`}
                >
                  Create Account
                </button>
              </div>

              {error && (
                <div className="flex items-start gap-2 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs mb-4">
                  <AlertCircle size={16} className="shrink-0 mt-0.5 text-red-500" />
                  <span>{error}</span>
                </div>
              )}

              {tab === "login" ? (
                /* LOGIN FORM */
                <form onSubmit={handleLoginSubmit} className="space-y-4">
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider mb-1.5" style={{ color: MUTED }}>
                      Email Address
                    </label>
                    <div
                      className="flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl border bg-slate-50/60 focus-within:bg-white focus-within:border-emerald-500 transition-all"
                      style={{ borderColor: BORDER }}
                    >
                      <Mail size={16} color={MUTED} />
                      <input
                        type="email"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="you@domain.com"
                        className="bg-transparent outline-none text-xs flex-1 text-slate-800 placeholder:text-slate-400"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider mb-1.5" style={{ color: MUTED }}>
                      Password
                    </label>
                    <div
                      className="flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl border bg-slate-50/60 focus-within:bg-white focus-within:border-emerald-500 transition-all"
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
                    className="w-full mt-3 py-3 rounded-xl text-xs font-semibold text-white flex items-center justify-center gap-2 shadow-md hover:brightness-105 active:scale-[0.99] disabled:opacity-60 transition-all"
                    style={{ background: NAVY }}
                  >
                    {isLoading ? (
                      <>
                        <Loader2 size={15} className="animate-spin" />
                        Signing in...
                      </>
                    ) : (
                      "Sign In"
                    )}
                  </button>
                </form>
              ) : (
                /* SIGNUP FORM */
                <form onSubmit={handleSignupSubmit} className="space-y-3.5">
                  {/* Role Selector Grid */}
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider mb-1.5" style={{ color: MUTED }}>
                      Select Profile Role
                    </label>
                    <div className="grid grid-cols-2 gap-3">
                      {[
                        { id: "layman", label: "Layman (Public User)", icon: UserIcon },
                        { id: "lawyer", label: "Lawyer / Advocate", icon: Briefcase },
                      ].map((item) => {
                        const Icon = item.icon;
                        const active = role === item.id;
                        return (
                          <button
                            key={item.id}
                            type="button"
                            onClick={() => setRole(item.id as any)}
                            className={`flex flex-col items-center justify-center py-3 px-2 rounded-xl border text-center transition-all ${
                              active
                                ? "border-emerald-600 bg-emerald-50 text-emerald-800 font-semibold ring-1 ring-emerald-600 shadow-sm"
                                : "border-slate-200 bg-slate-50/50 text-slate-600 hover:bg-slate-100"
                            }`}
                          >
                            <Icon size={20} className={active ? "text-emerald-700" : "text-slate-500"} />
                            <span className="text-xs mt-1.5">{item.label}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Full Name */}
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: MUTED }}>
                      Full Name
                    </label>
                    <div
                      className="flex items-center gap-2.5 px-3 py-2 rounded-xl border bg-slate-50/60 focus-within:bg-white focus-within:border-emerald-500 transition-all"
                      style={{ borderColor: BORDER }}
                    >
                      <UserIcon size={15} color={MUTED} />
                      <input
                        type="text"
                        required
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="e.g. Barrister Ali Khan"
                        className="bg-transparent outline-none text-xs flex-1 text-slate-800 placeholder:text-slate-400"
                      />
                    </div>
                  </div>

                  {/* Email */}
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: MUTED }}>
                      Email Address
                    </label>
                    <div
                      className="flex items-center gap-2.5 px-3 py-2 rounded-xl border bg-slate-50/60 focus-within:bg-white focus-within:border-emerald-500 transition-all"
                      style={{ borderColor: BORDER }}
                    >
                      <Mail size={15} color={MUTED} />
                      <input
                        type="email"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="you@domain.com"
                        className="bg-transparent outline-none text-xs flex-1 text-slate-800 placeholder:text-slate-400"
                      />
                    </div>
                  </div>

                  {/* Password */}
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: MUTED }}>
                      Password
                    </label>
                    <div
                      className="flex items-center gap-2.5 px-3 py-2 rounded-xl border bg-slate-50/60 focus-within:bg-white focus-within:border-emerald-500 transition-all"
                      style={{ borderColor: BORDER }}
                    >
                      <Lock size={15} color={MUTED} />
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

                  {/* Conditional Role Fields (From DB Schema) */}
                  {role === "lawyer" && (
                    <div className="grid grid-cols-2 gap-2.5 pt-1">
                      <div>
                        <label className="block text-[11px] font-semibold uppercase tracking-wider mb-1" style={{ color: MUTED }}>
                          Bar License No
                        </label>
                        <div
                          className="flex items-center gap-2 px-3 py-2 rounded-xl border bg-slate-50/60 focus-within:bg-white focus-within:border-emerald-500 transition-all"
                          style={{ borderColor: BORDER }}
                        >
                          <FileBadge size={14} color={MUTED} />
                          <input
                            type="text"
                            required
                            value={licenseNo}
                            onChange={(e) => setLicenseNo(e.target.value)}
                            placeholder="LHC-12345"
                            className="bg-transparent outline-none text-xs flex-1"
                          />
                        </div>
                      </div>
                      <div>
                        <label className="block text-[11px] font-semibold uppercase tracking-wider mb-1" style={{ color: MUTED }}>
                          CNIC Number
                        </label>
                        <div
                          className="flex items-center gap-2 px-3 py-2 rounded-xl border bg-slate-50/60 focus-within:bg-white focus-within:border-emerald-500 transition-all"
                          style={{ borderColor: BORDER }}
                        >
                          <CreditCard size={14} color={MUTED} />
                          <input
                            type="text"
                            required
                            value={cnic}
                            onChange={(e) => setCnic(e.target.value)}
                            placeholder="35201-xxxxxxx-x"
                            className="bg-transparent outline-none text-xs flex-1"
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={isLoading}
                    className="w-full mt-2 py-3 rounded-xl text-xs font-semibold text-white flex items-center justify-center gap-2 shadow-md hover:brightness-105 active:scale-[0.99] disabled:opacity-60 transition-all"
                    style={{ background: NAVY }}
                  >
                    {isLoading ? (
                      <>
                        <Loader2 size={15} className="animate-spin" />
                        Creating Account...
                      </>
                    ) : (
                      `Register as ${role.toUpperCase()}`
                    )}
                  </button>
                </form>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
