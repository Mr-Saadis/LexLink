import React, { useState } from "react";
import { useAuth } from "../context/AuthContext";
import {
  Scale,
  Lock,
  Mail,
  User as UserIcon,
  Briefcase,
  FileBadge,
  CreditCard,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Eye,
  EyeOff,
  Shield,
  ArrowRight,
} from "lucide-react";

interface AuthPageProps {
  onLoginSuccess: (role: string) => void;
}

export default function AuthPage({ onLoginSuccess }: AuthPageProps) {
  const { login, signup, error, isLoading, user, logout } = useAuth();

  const [tab, setTab] = useState<"login" | "signup">("login");
  const [role, setRole] = useState<"layman" | "lawyer">("layman");
  const [showPassword, setShowPassword] = useState(false);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [licenseNo, setLicenseNo] = useState("");
  const [cnic, setCnic] = useState("");

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;
    const loggedUser = await login(email, password);
    if (loggedUser) {
      onLoginSuccess(loggedUser.role || "layman");
    }
  };

  const handleSignupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password || !name) return;
    const registeredUser = await signup({
      email,
      password,
      name,
      role,
      license_no: role === "lawyer" ? licenseNo : undefined,
      cnic: role === "lawyer" ? cnic : undefined,
    });
    if (registeredUser) {
      onLoginSuccess(registeredUser.role || "layman");
    }
  };

  return (
    <div
      className="min-h-screen flex"
      style={{ background: "linear-gradient(135deg, #0a1628 0%, #064E3B 55%, #0d2137 100%)" }}
    >
      {/* Left Branding Panel */}
      <div className="hidden lg:flex flex-col justify-between w-[44%] p-12 relative overflow-hidden">
        <div className="absolute -top-32 -left-32 w-96 h-96 rounded-full opacity-10" style={{ background: "#10B981" }} />
        <div className="absolute bottom-20 -right-16 w-72 h-72 rounded-full opacity-[0.06]" style={{ background: "#10B981" }} />

        <div className="relative z-10 flex items-center gap-4">
          <div
            className="w-12 h-12 rounded-2xl flex items-center justify-center"
            style={{ background: "linear-gradient(135deg, #10B981 0%, #047857 100%)", boxShadow: "0 0 28px rgba(16,185,129,0.4)" }}
          >
            <Scale size={22} color="#fff" />
          </div>
          <div>
            <span className="text-white text-xl font-bold tracking-tight block leading-none">LexLink</span>
            <span className="text-emerald-400 text-[10px] font-medium tracking-widest uppercase">Legal Intelligence</span>
          </div>
        </div>

        <div className="relative z-10">
          <h1 className="text-white text-4xl font-bold leading-snug mb-5">
            Pakistan's National<br />
            <span style={{ color: "#10B981" }}>Legal Research</span><br />
            Platform
          </h1>
          <p className="text-slate-400 text-sm leading-relaxed max-w-sm">
            Unified access to Supreme Court &amp; High Court judgments with AI-powered
            search, semantic analysis, and legal case prediction.
          </p>
          <div className="mt-10 grid grid-cols-3 gap-6">
            {[{ label: "Judgments", value: "50K+" }, { label: "Courts", value: "2" }, { label: "Languages", value: "3" }].map((s) => (
              <div key={s.label}>
                <div className="text-2xl font-bold text-white">{s.value}</div>
                <div className="text-xs text-slate-500 mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="relative z-10 flex items-center gap-2 text-[11px] text-slate-600">
          <Shield size={12} />
          <span>Secured by Supabase Auth &amp; encrypted JWT sessions</span>
        </div>
      </div>

      {/* Right Form Panel */}
      <div className="flex-1 flex items-center justify-center p-6 lg:p-12">
        <div
          className="w-full max-w-md rounded-2xl overflow-hidden"
          style={{
            background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.08)",
            backdropFilter: "blur(24px)",
            boxShadow: "0 32px 64px rgba(0,0,0,0.5)",
          }}
        >
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-3 px-8 pt-8 mb-2">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: "linear-gradient(135deg, #10B981 0%, #047857 100%)" }}>
              <Scale size={18} color="#fff" />
            </div>
            <div>
              <span className="text-white font-bold text-base block leading-none">LexLink</span>
              <span className="text-emerald-400 text-[10px] tracking-widest uppercase">Legal Intelligence</span>
            </div>
          </div>

          {user ? (
            <div className="p-8">
              <div className="flex flex-col items-center text-center mb-6">
                <div className="w-16 h-16 rounded-full flex items-center justify-center mb-4" style={{ background: "rgba(16,185,129,0.15)", border: "2px solid rgba(16,185,129,0.3)" }}>
                  <CheckCircle2 size={28} color="#10B981" />
                </div>
                <h2 className="text-white text-xl font-bold mb-1">Session Active</h2>
                <p className="text-slate-400 text-xs">Your session is authenticated and verified.</p>
              </div>

              <div className="rounded-xl p-4 mb-6 space-y-3" style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)" }}>
                {[
                  { label: "Name", value: user.name || "Administrator" },
                  { label: "Email", value: user.email },
                  { label: "Role", value: (user.role || "USER").toUpperCase(), badge: true },
                ].map((row) => (
                  <div key={row.label} className="flex justify-between items-center text-xs">
                    <span className="text-slate-500">{row.label}</span>
                    {row.badge ? (
                      <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold" style={{ background: "rgba(16,185,129,0.15)", color: "#10B981", border: "1px solid rgba(16,185,129,0.3)" }}>
                        {row.value}
                      </span>
                    ) : (
                      <span className="text-white font-medium">{row.value}</span>
                    )}
                  </div>
                ))}
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => onLoginSuccess(user.role || "layman")}
                  className="flex-1 py-3 rounded-xl text-xs font-semibold text-white flex items-center justify-center gap-2 transition-all hover:brightness-110 active:scale-[0.99]"
                  style={{ background: "linear-gradient(135deg, #10B981 0%, #047857 100%)" }}
                >
                  Continue to {user.role === "admin" ? "Dashboard" : "Console"}
                  <ArrowRight size={14} />
                </button>
                <button
                  onClick={logout}
                  className="px-4 py-3 rounded-xl text-xs font-semibold transition-colors"
                  style={{ background: "rgba(239,68,68,0.1)", color: "#EF4444", border: "1px solid rgba(239,68,68,0.2)" }}
                >
                  Sign Out
                </button>
              </div>
            </div>
          ) : (
            <div className="p-8">
              <div className="mb-7">
                <h2 className="text-white text-2xl font-bold tracking-tight mb-1">
                  {tab === "login" ? "Welcome back" : "Create account"}
                </h2>
                <p className="text-slate-500 text-xs">
                  {tab === "login" ? "Sign in to access the legal research console." : "Register as an advocate or public citizen."}
                </p>
              </div>

              <div className="flex rounded-xl p-1 mb-6" style={{ background: "rgba(255,255,255,0.05)" }}>
                {(["login", "signup"] as const).map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => setTab(t)}
                    className="flex-1 py-2 text-xs font-semibold rounded-lg transition-all"
                    style={tab === t ? { background: "rgba(16,185,129,0.2)", color: "#10B981", border: "1px solid rgba(16,185,129,0.3)" } : { color: "#64748B" }}
                  >
                    {t === "login" ? "Sign In" : "Create Account"}
                  </button>
                ))}
              </div>

              {error && (
                <div className="flex items-start gap-2 p-3 rounded-xl text-xs mb-5" style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.2)", color: "#FCA5A5" }}>
                  <AlertCircle size={14} className="shrink-0 mt-0.5" />
                  <span>{error}</span>
                </div>
              )}

              {tab === "login" ? (
                <form onSubmit={handleLoginSubmit} className="space-y-4">
                  <DarkInput label="Email Address" icon={<Mail size={15} color="#64748B" />} type="email" value={email} onChange={setEmail} placeholder="name@example.com" required />

                  <div>
                    <label className="block text-xs font-semibold text-slate-400 mb-1.5">Password</label>
                    <div className="flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl" style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}>
                      <Lock size={15} color="#64748B" />
                      <input
                        type={showPassword ? "text" : "password"}
                        required
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="••••••••••••"
                        className="bg-transparent outline-none text-xs flex-1 text-white placeholder:text-slate-600"
                      />
                      <button type="button" onClick={() => setShowPassword(!showPassword)} className="text-slate-600 hover:text-slate-400 transition-colors">
                        {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                      </button>
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={isLoading}
                    className="w-full mt-2 py-3 rounded-xl text-xs font-semibold text-white flex items-center justify-center gap-2 transition-all hover:brightness-110 active:scale-[0.99] disabled:opacity-50"
                    style={{ background: "linear-gradient(135deg, #10B981 0%, #047857 100%)", boxShadow: "0 4px 16px rgba(16,185,129,0.3)" }}
                  >
                    {isLoading ? <><Loader2 size={14} className="animate-spin" /> Authenticating...</> : <>Sign In <ArrowRight size={14} /></>}
                  </button>

                  <p className="text-center text-[11px] text-slate-600 pt-1">
                    Admin access is pre-configured.{" "}
                    <span className="text-emerald-600">No signup required.</span>
                  </p>
                </form>
              ) : (
                <form onSubmit={handleSignupSubmit} className="space-y-3.5">
                  <div>
                    <label className="block text-xs font-semibold text-slate-400 mb-2">Account Type</label>
                    <div className="grid grid-cols-2 gap-2">
                      {([
                        { id: "layman" as const, label: "Public Citizen", Icon: UserIcon },
                        { id: "lawyer" as const, label: "Advocate / Lawyer", Icon: Briefcase },
                      ]).map(({ id, label, Icon }) => (
                        <button
                          key={id}
                          type="button"
                          onClick={() => setRole(id)}
                          className="flex items-center gap-2 py-2.5 px-3 rounded-xl text-left transition-all"
                          style={role === id
                            ? { background: "rgba(16,185,129,0.15)", border: "1px solid rgba(16,185,129,0.4)", color: "#10B981" }
                            : { background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)", color: "#64748B" }}
                        >
                          <Icon size={14} />
                          <span className="text-xs font-medium">{label}</span>
                        </button>
                      ))}
                    </div>
                  </div>

                  <DarkInput label="Full Name" icon={<UserIcon size={15} color="#64748B" />} type="text" value={name} onChange={setName} placeholder="e.g. Barrister Ali Khan" required />
                  <DarkInput label="Email Address" icon={<Mail size={15} color="#64748B" />} type="email" value={email} onChange={setEmail} placeholder="name@example.com" required />

                  <div>
                    <label className="block text-xs font-semibold text-slate-400 mb-1.5">Password</label>
                    <div className="flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl" style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}>
                      <Lock size={15} color="#64748B" />
                      <input
                        type={showPassword ? "text" : "password"}
                        required
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="••••••••••••"
                        className="bg-transparent outline-none text-xs flex-1 text-white placeholder:text-slate-600"
                      />
                      <button type="button" onClick={() => setShowPassword(!showPassword)} className="text-slate-600 hover:text-slate-400 transition-colors">
                        {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                      </button>
                    </div>
                  </div>

                  {role === "lawyer" && (
                    <div className="grid grid-cols-2 gap-2.5 pt-1">
                      <DarkInput label="Bar License No" icon={<FileBadge size={14} color="#64748B" />} type="text" value={licenseNo} onChange={setLicenseNo} placeholder="LHC-12345" required />
                      <DarkInput label="CNIC Number" icon={<CreditCard size={14} color="#64748B" />} type="text" value={cnic} onChange={setCnic} placeholder="35201-xxxxxxx-x" required />
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={isLoading}
                    className="w-full mt-2 py-3 rounded-xl text-xs font-semibold text-white flex items-center justify-center gap-2 transition-all hover:brightness-110 active:scale-[0.99] disabled:opacity-50"
                    style={{ background: "linear-gradient(135deg, #10B981 0%, #047857 100%)", boxShadow: "0 4px 16px rgba(16,185,129,0.3)" }}
                  >
                    {isLoading
                      ? <><Loader2 size={14} className="animate-spin" /> Creating Account...</>
                      : <>{`Register as ${role === "lawyer" ? "Advocate" : "Public User"}`} <ArrowRight size={14} /></>}
                  </button>
                </form>
              )}
            </div>
          )}

          <div className="px-8 py-4 text-center text-[11px]" style={{ borderTop: "1px solid rgba(255,255,255,0.05)", color: "#334155" }}>
            LexLink Legal Intelligence • Supreme Court &amp; High Court Portal
          </div>
        </div>
      </div>
    </div>
  );
}

interface DarkInputProps {
  label: string;
  icon: React.ReactNode;
  type: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  required?: boolean;
}

function DarkInput({ label, icon, type, value, onChange, placeholder, required }: DarkInputProps) {
  return (
    <div>
      <label className="block text-xs font-semibold text-slate-400 mb-1.5">{label}</label>
      <div className="flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl" style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}>
        {icon}
        <input
          type={type}
          required={required}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="bg-transparent outline-none text-xs flex-1 text-white placeholder:text-slate-600"
        />
      </div>
    </div>
  );
}
