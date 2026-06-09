"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { LockKeyhole, User, ShieldAlert, ArrowRight, Activity, ShieldCheck, Database, KeyRound } from "lucide-react";

export default function AdminLoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<{ username?: string; password?: string; general?: string }>({});
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const validate = () => {
    const normalizedUsername = username.trim();
    const newErrors: { username?: string; password?: string } = {};
    if (!normalizedUsername || normalizedUsername.length < 3) {
      newErrors.username = "Username must be at least 3 characters long.";
    }
    if (!password || password.length < 8) {
      newErrors.password = "Password must be at least 8 characters long.";
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    const normalizedUsername = username.trim();

    setIsLoading(true);
    setErrors({});

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: normalizedUsername, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        setErrors({ general: data.detail || "Authentication failed. Please try again." });
        return;
      }

      router.push("/dashboard");
    } catch {
      setErrors({ general: "An unexpected error occurred." });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen bg-[#0A0A0B] text-slate-200 overflow-hidden px-4 py-10 sm:px-6 lg:px-8 selection:bg-blue-500/30">
      {/* Premium Background Effects */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-blue-600/10 blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-indigo-600/10 blur-[120px]" />
        <div className="absolute top-[40%] left-[60%] w-[30%] h-[30%] rounded-full bg-violet-600/10 blur-[100px]" />
        <div className="absolute inset-0 bg-[url('/noise.png')] opacity-[0.03] mix-blend-overlay" />
      </div>

      <div className="relative z-10 mx-auto grid w-full max-w-6xl items-center gap-12 lg:grid-cols-2 lg:h-[calc(100vh-80px)]">
        
        {/* Left Side: Brand & Features */}
        <div className="animate-in fade-in slide-in-from-left-8 duration-1000 lg:pr-10 flex flex-col justify-center h-full">
          <div className="inline-flex items-center gap-2 rounded-full border border-blue-500/30 bg-blue-500/10 px-4 py-1.5 text-xs font-medium tracking-wide text-blue-400 mb-8 w-fit backdrop-blur-md">
            <ShieldAlert className="w-4 h-4" /> SECURE ADMIN PORTAL
          </div>
          
          <h1 className="text-balance text-5xl font-extrabold tracking-tight text-white sm:text-6xl lg:text-7xl">
            Security <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-500">Command</span> Center
          </h1>
          
          <p className="mt-6 max-w-xl text-base text-slate-400 sm:text-lg font-light leading-relaxed">
            Advanced real-time analytics and monitoring for organizational password security. Track anomalies, monitor compliance, and enforce policies.
          </p>

          <div className="mt-12 grid gap-5 sm:grid-cols-2">
            {[
              { icon: Activity, title: "Live Telemetry", desc: "Real-time authentication tracking" },
              { icon: ShieldCheck, title: "Threat Detection", desc: "Automated breach monitoring" },
              { icon: Database, title: "Audit Logs", desc: "Immutable security records" },
              { icon: KeyRound, title: "Policy Engine", desc: "Advanced strength requirements" }
            ].map((feature, idx) => (
              <div key={idx} className="group rounded-2xl border border-white/5 bg-white/[0.02] p-5 backdrop-blur-xl transition-all duration-300 hover:bg-white/[0.04] hover:border-white/10 hover:-translate-y-1">
                <div className="mb-4 inline-flex rounded-xl bg-gradient-to-br from-blue-500/20 to-indigo-500/20 p-2.5 text-blue-400 ring-1 ring-white/10 transition-colors group-hover:from-blue-500/30 group-hover:to-indigo-500/30">
                  <feature.icon className="w-5 h-5" />
                </div>
                <h3 className="font-semibold text-slate-200">{feature.title}</h3>
                <p className="mt-1.5 text-sm text-slate-400">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Right Side: Login Form */}
        <div className="relative mx-auto w-full max-w-md animate-in fade-in slide-in-from-right-8 duration-1000 lg:mx-0">
          
          {/* Decorative elements behind form */}
          <div className="absolute -inset-1 rounded-3xl bg-gradient-to-br from-blue-500/20 via-transparent to-indigo-500/20 blur-xl opacity-50" />
          
          <div className="relative rounded-3xl border border-white/10 bg-[#121214]/80 p-8 shadow-2xl backdrop-blur-2xl sm:p-10">
            <div className="mb-8 text-center">
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/30">
                <LockKeyhole className="h-6 w-6 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-white tracking-tight">Admin Authentication</h2>
              <p className="mt-2 text-sm text-slate-400">Enter your credentials to access the dashboard</p>
            </div>

            <form className="space-y-6" onSubmit={handleSubmit}>
              {errors.general && (
                <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 animate-in fade-in zoom-in-95 duration-300 backdrop-blur-md">
                  <div className="flex items-center gap-3">
                    <ShieldAlert className="w-5 h-5 text-rose-400 shrink-0" />
                    <p className="text-sm font-medium text-rose-300">{errors.general}</p>
                  </div>
                </div>
              )}

              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 pl-1">Username</label>
                <div className="relative group">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-500 group-focus-within:text-blue-400 transition-colors">
                    <User className="h-5 w-5" />
                  </div>
                  <input
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className={`block w-full rounded-xl border ${
                      errors.username
                        ? "border-rose-500/50 bg-rose-500/5 focus:border-rose-500 focus:ring-rose-500/20"
                        : "border-white/10 bg-white/5 focus:border-blue-500 focus:ring-blue-500/20"
                    } py-3.5 pl-11 pr-4 text-sm text-white shadow-sm outline-none transition-all duration-300 placeholder:text-slate-500`}
                    placeholder="Enter admin username"
                  />
                </div>
                {errors.username && <p className="mt-1.5 text-xs text-rose-400 pl-1">{errors.username}</p>}
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 pl-1">Password</label>
                <div className="relative group">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-500 group-focus-within:text-blue-400 transition-colors">
                    <LockKeyhole className="h-5 w-5" />
                  </div>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className={`block w-full rounded-xl border ${
                      errors.password
                        ? "border-rose-500/50 bg-rose-500/5 focus:border-rose-500 focus:ring-rose-500/20"
                        : "border-white/10 bg-white/5 focus:border-blue-500 focus:ring-blue-500/20"
                    } py-3.5 pl-11 pr-4 text-sm text-white shadow-sm outline-none transition-all duration-300 placeholder:text-slate-500`}
                    placeholder="••••••••••••"
                  />
                </div>
                {errors.password && <p className="mt-1.5 text-xs text-rose-400 pl-1">{errors.password}</p>}
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="group relative w-full flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-3.5 text-sm font-semibold text-white shadow-[0_0_20px_rgba(37,99,235,0.2)] transition-all duration-300 hover:shadow-[0_0_30px_rgba(37,99,235,0.4)] hover:from-blue-500 hover:to-indigo-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-[#121214] disabled:opacity-50 overflow-hidden"
              >
                <div className="absolute inset-0 w-full h-full bg-white/20 translate-x-[-100%] group-hover:animate-[shimmer_1.5s_infinite]" />
                {isLoading ? (
                  <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                  </svg>
                ) : (
                  <>
                    Sign In to Portal
                    <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
                  </>
                )}
              </button>
            </form>
            
            <div className="mt-8 pt-6 border-t border-white/10">
              <p className="text-center text-xs text-slate-500 flex items-center justify-center gap-2">
                <ShieldCheck className="w-3.5 h-3.5" />
                Protected by military-grade encryption
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
