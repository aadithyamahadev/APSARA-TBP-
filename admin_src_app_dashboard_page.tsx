"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Shield, Lock, Unlock, AlertTriangle, AlertCircle, ShieldCheck, Activity, Key, LogOut, CheckCircle2, ChevronRight, BarChart3, Database } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from "recharts";
import PasswordResult, { ResultType } from "@/components/PasswordResult";

interface DashboardMetrics {
  total_checks: number;
  strength_distribution: Record<string, number>;
  risk_distribution: Record<string, number>;
  breached_passwords: number;
  average_score: number;
  score_ranges: Record<string, number>;
  breached_percentage: number;
}

interface PasswordCheck {
  id: string;
  user_id: string | null;
  score: number;
  strength_label: string;
  risk_label: string;
  is_breached: boolean;
  breach_count: number;
  created_at: string;
}

const STRENGTH_COLORS: Record<string, string> = {
  "very weak": "#ef4444",
  weak: "#f97316",
  fair: "#eab308",
  good: "#3b82f6",
  strong: "#22c55e",
  "very strong": "#10b981",
};

export default function AdminDashboard() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [recentChecks, setRecentChecks] = useState<PasswordCheck[]>([]);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [scoring, setScoring] = useState(false);
  const [scoreError, setScoreError] = useState("");
  const [scoreResult, setScoreResult] = useState<ResultType | null>(null);
  const router = useRouter();

  const fetchDashboardData = async () => {
    try {
      const [metricsRes, checksRes, timelineRes] = await Promise.all([
        fetch("/api/dashboard/metrics"),
        fetch("/api/dashboard/recent-checks?limit=8"),
        fetch("/api/dashboard/timeline?days=7")
      ]);

      if (metricsRes.status === 401) {
        router.push("/login");
        return;
      }

      const [metricsData, checksData, timelineData] = await Promise.all([
        metricsRes.json(),
        checksRes.json(),
        timelineRes.ok ? timelineRes.json() : { timeline: [] }
      ]);

      setMetrics(metricsData);
      setRecentChecks(checksData);
      
      if (timelineData.timeline) {
        setTimeline(timelineData.timeline.map((item: any) => ({
          date: new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
          score: item.average_score,
          checks: item.check_count
        })));
      }
    } catch (err) {
      setError("Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [router]);

  const handleScore = async () => {
    if (!password.trim()) {
      setScoreError("Enter a password to analyze.");
      return;
    }

    setScoring(true);
    setScoreError("");
    try {
      const resp = await fetch("/api/score", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });

      if (resp.status === 401) {
        router.push("/login");
        return;
      }

      const data = await resp.json();
      if (!resp.ok) {
        setScoreError(data.error || "Failed to score password.");
        return;
      }

      setScoreResult(data);
      await fetchDashboardData();
    } catch {
      setScoreError("Unexpected error while scoring password.");
    } finally {
      setScoring(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#0A0A0B]">
        <div className="text-center animate-in fade-in zoom-in duration-500">
          <div className="mb-6 relative">
            <Shield className="w-16 h-16 text-blue-500/20 animate-pulse mx-auto" />
            <Activity className="w-8 h-8 text-blue-500 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
          </div>
          <p className="text-slate-400 font-medium tracking-wide uppercase text-sm">Initializing Secure Environment</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0A0B] text-slate-200 selection:bg-blue-500/30 font-sans pb-12">
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-blue-600/5 blur-[150px]" />
        <div className="absolute bottom-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-indigo-600/5 blur-[150px]" />
        <div className="absolute top-[30%] left-[30%] w-[40%] h-[40%] rounded-full bg-violet-600/5 blur-[120px]" />
      </div>

      <nav className="sticky top-0 z-50 border-b border-white/10 bg-[#0A0A0B]/80 backdrop-blur-xl">
        <div className="mx-auto max-w-[1600px] px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/20">
              <ShieldCheck className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white tracking-tight">Security Command Center</h1>
              <p className="text-xs text-blue-400 font-medium tracking-wider uppercase">Live Telemetry</p>
            </div>
          </div>
          
          <button
            onClick={() => router.push("/login")}
            className="group flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-300 transition-all hover:bg-white/10 hover:text-white"
          >
            <LogOut className="w-4 h-4 transition-transform group-hover:-translate-x-0.5" />
            Terminate Session
          </button>
        </div>
      </nav>

      <main className="relative z-10 mx-auto max-w-[1600px] px-6 mt-8 space-y-8 animate-in fade-in slide-in-from-bottom-8 duration-700">
        
        {metrics && (
          <div className="grid gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
            <div className="group relative overflow-hidden rounded-2xl border border-white/10 bg-white/[0.02] p-6 backdrop-blur-xl transition-all hover:bg-white/[0.04] hover:border-white/20">
              <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Total Checks</p>
                  <p className="mt-2 text-4xl font-bold text-white tracking-tight">{metrics.total_checks.toLocaleString()}</p>
                </div>
                <div className="p-3 rounded-xl bg-blue-500/10 text-blue-400">
                  <Database className="w-6 h-6" />
                </div>
              </div>
              <p className="mt-4 text-xs text-slate-500 flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5 text-blue-400" /> Live evaluations across platform
              </p>
            </div>

            <div className="group relative overflow-hidden rounded-2xl border border-white/10 bg-white/[0.02] p-6 backdrop-blur-xl transition-all hover:bg-white/[0.04] hover:border-white/20">
              <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/10 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Average Score</p>
                  <div className="mt-2 flex items-baseline gap-2">
                    <p className="text-4xl font-bold text-white tracking-tight">{metrics.average_score}</p>
                    <span className="text-sm font-medium text-slate-500">/ 100</span>
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-indigo-500/10 text-indigo-400">
                  <BarChart3 className="w-6 h-6" />
                </div>
              </div>
              <div className="mt-4 h-1.5 w-full bg-white/10 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-blue-500 to-indigo-500" style={{ width: `${metrics.average_score}%` }} />
              </div>
            </div>

            <div className="group relative overflow-hidden rounded-2xl border border-rose-500/20 bg-rose-500/5 p-6 backdrop-blur-xl transition-all hover:bg-rose-500/10 hover:border-rose-500/30">
              <div className="absolute inset-0 bg-gradient-to-br from-rose-500/10 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-rose-400">Compromised</p>
                  <p className="mt-2 text-4xl font-bold text-rose-500 tracking-tight">{metrics.breached_passwords.toLocaleString()}</p>
                </div>
                <div className="p-3 rounded-xl bg-rose-500/20 text-rose-400 animate-pulse">
                  <AlertTriangle className="w-6 h-6" />
                </div>
              </div>
              <p className="mt-4 text-xs text-rose-400/80 flex items-center gap-1.5">
                <AlertCircle className="w-3.5 h-3.5" /> {metrics.breached_percentage}% of total scans
              </p>
            </div>

            <div className="group relative overflow-hidden rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-6 backdrop-blur-xl transition-all hover:bg-emerald-500/10 hover:border-emerald-500/30">
              <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/10 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-emerald-400">High Security</p>
                  <p className="mt-2 text-4xl font-bold text-emerald-500 tracking-tight">
                    {((metrics.strength_distribution["strong"] || 0) + (metrics.strength_distribution["very strong"] || 0)).toLocaleString()}
                  </p>
                </div>
                <div className="p-3 rounded-xl bg-emerald-500/20 text-emerald-400">
                  <ShieldCheck className="w-6 h-6" />
                </div>
              </div>
              <p className="mt-4 text-xs text-emerald-400/80 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" /> Passwords scoring 70+
              </p>
            </div>
          </div>
        )}

        <div className="grid gap-8 lg:grid-cols-3">
          
          <div className="lg:col-span-1 space-y-8">
            <div className="rounded-3xl border border-white/10 bg-[#121214]/80 p-6 backdrop-blur-2xl shadow-xl">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 rounded-lg bg-blue-500/20 text-blue-400">
                  <Key className="w-5 h-5" />
                </div>
                <h2 className="text-lg font-semibold text-white">Live Diagnostics</h2>
              </div>
              
              <div className="space-y-4">
                <div className="relative group">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-500 group-focus-within:text-blue-400">
                    {showPassword ? <Unlock className="w-4 h-4" /> : <Lock className="w-4 h-4" />}
                  </div>
                  <input
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter payload to analyze..."
                    className="block w-full rounded-xl border border-white/10 bg-black/50 py-3.5 pl-11 pr-16 text-sm text-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all placeholder:text-slate-600"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-4 flex items-center text-xs font-semibold text-slate-500 hover:text-white transition-colors"
                  >
                    {showPassword ? "HIDE" : "SHOW"}
                  </button>
                </div>
                
                {scoreError && <p className="text-xs text-rose-400 font-medium">{scoreError}</p>}

                <div className="flex gap-3">
                  <button
                    onClick={handleScore}
                    disabled={scoring}
                    className="flex-1 rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-500/20 transition-all hover:bg-blue-500 hover:shadow-blue-500/40 disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {scoring ? <Activity className="w-4 h-4 animate-spin" /> : "Run Analysis"}
                  </button>
                  <button
                    onClick={() => { setPassword(""); setScoreResult(null); setScoreError(""); }}
                    className="rounded-xl border border-white/10 bg-white/5 px-6 py-3 text-sm font-semibold text-slate-300 transition-all hover:bg-white/10 hover:text-white"
                  >
                    Clear
                  </button>
                </div>
              </div>

              {scoreResult && (
                <div className="mt-6 pt-6 border-t border-white/10 animate-in fade-in slide-in-from-top-4 duration-500">
                  <PasswordResult result={scoreResult} />
                </div>
              )}
            </div>

            {metrics && (
              <div className="rounded-3xl border border-white/10 bg-[#121214]/80 p-6 backdrop-blur-2xl shadow-xl">
                <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400 mb-6">Strength Distribution</h2>
                <div className="h-48 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={Object.entries(metrics.strength_distribution).map(([name, value]) => ({ name, value }))} layout="vertical" margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                      <XAxis type="number" hide />
                      <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 12 }} width={80} />
                      <Tooltip 
                        cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                        contentStyle={{ backgroundColor: '#121214', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', color: '#fff' }}
                      />
                      <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                        {Object.entries(metrics.strength_distribution).map(([name, _], index) => (
                          <Cell key={`cell-${index}`} fill={STRENGTH_COLORS[name] || '#3b82f6'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </div>

          <div className="lg:col-span-2 space-y-8">
            
            <div className="rounded-3xl border border-white/10 bg-[#121214]/80 p-6 backdrop-blur-2xl shadow-xl h-[340px] flex flex-col">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400 mb-6 flex items-center gap-2">
                <Activity className="w-4 h-4 text-blue-400" /> 7-Day Strength Timeline
              </h2>
              <div className="flex-1 w-full h-full -ml-4">
                {timeline.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={timeline} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} dy={10} />
                      <YAxis axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} dx={-10} domain={[0, 100]} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#121214', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', color: '#fff' }}
                        itemStyle={{ color: '#fff' }}
                      />
                      <Area type="monotone" dataKey="score" stroke="#3b82f6" strokeWidth={3} fillOpacity={1} fill="url(#colorScore)" />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center">
                    <p className="text-slate-500 text-sm font-medium">Insufficient telemetry data for timeline.</p>
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-3xl border border-white/10 bg-[#121214]/80 backdrop-blur-2xl shadow-xl overflow-hidden">
              <div className="px-6 py-5 border-b border-white/10 flex items-center justify-between">
                <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                  <Database className="w-4 h-4 text-indigo-400" /> Recent Telemetry Logs
                </h2>
                <button className="text-xs font-semibold text-blue-400 hover:text-blue-300 transition-colors flex items-center gap-1">
                  View Full Audit Log <ChevronRight className="w-3 h-3" />
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-white/[0.02] border-b border-white/5">
                      <th className="px-6 py-4 text-xs font-semibold text-slate-400">SCORE</th>
                      <th className="px-6 py-4 text-xs font-semibold text-slate-400">STRENGTH</th>
                      <th className="px-6 py-4 text-xs font-semibold text-slate-400">RISK VECTOR</th>
                      <th className="px-6 py-4 text-xs font-semibold text-slate-400">BREACH STATUS</th>
                      <th className="px-6 py-4 text-xs font-semibold text-slate-400">TIMESTAMP</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {recentChecks.map((check) => (
                      <tr key={check.id} className="transition-colors hover:bg-white/[0.02]">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold shadow-inner ${check.score > 70 ? 'bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-500/30' : check.score > 40 ? 'bg-yellow-500/20 text-yellow-400 ring-1 ring-yellow-500/30' : 'bg-rose-500/20 text-rose-400 ring-1 ring-rose-500/30'}`}>
                            {check.score}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="capitalize font-medium text-slate-300 text-sm flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: STRENGTH_COLORS[check.strength_label] || '#94a3b8' }} />
                            {check.strength_label}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-400 capitalize">
                          {check.risk_label}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          {check.is_breached ? (
                            <div className="inline-flex items-center gap-1.5 rounded-full bg-rose-500/10 px-3 py-1 text-xs font-semibold text-rose-400 border border-rose-500/20">
                              <AlertCircle className="w-3.5 h-3.5" /> Breached ({check.breach_count})
                            </div>
                          ) : (
                            <div className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-400 border border-emerald-500/20">
                              <ShieldCheck className="w-3.5 h-3.5" /> Secure
                            </div>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-xs text-slate-500 font-mono">
                          {new Date(check.created_at).toLocaleString('en-US', { hour12: false })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            
          </div>
        </div>
      </main>
    </div>
  );
}
