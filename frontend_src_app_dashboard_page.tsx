"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import PasswordResult, { ResultType } from "@/components/PasswordResult";

export default function DashboardPage() {
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [result, setResult] = useState<ResultType | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  const handleClear = () => {
    setPassword("");
    setResult(null);
    setError("");
  };

  const handleScore = async () => {
    if (!password) {
      setError("Please enter a password to analyze");
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      const resp = await fetch("/api/score", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });

      if (resp.status === 401) {
        router.push("/auth");
        return;
      }

      if (!resp.ok) {
        const err = await resp.json();
        setError(err.error || "Failed to analyze password.");
        return;
      }

      const data = await resp.json();
      setResult(data);
    } catch {
      setError("An unexpected error occurred.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_12%_20%,#a7f3d088,transparent_30%),radial-gradient(circle_at_88%_80%,#67e8f988,transparent_40%)]" />
      <header className="relative border-b border-slate-200/70 bg-white/85 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-6 sm:px-6 lg:px-8">
          <div>
            <p className="text-xs font-semibold tracking-wider text-teal-700">APSARA SECURITY</p>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">Password Intelligence Dashboard</h1>
          </div>
          <button
            onClick={() => router.push("/auth")}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50"
          >
            Sign out
          </button>
        </div>
      </header>

      <main className="relative mx-auto max-w-4xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white/90 shadow-2xl backdrop-blur transition-all duration-300">
          <div className="px-6 py-8 sm:px-8">
            <h2 className="mb-2 text-xl font-semibold text-slate-900">Analyze Password Strength</h2>
            <p className="mb-6 text-sm text-slate-600">Enter a candidate password to evaluate score, breach risk, and targeted improvements.</p>
            <div className="mb-6 grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-3">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Session Security</p>
                <p className="mt-1 text-sm font-medium text-slate-800">Auth via httpOnly token cookie</p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-3">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Analysis Quality</p>
                <p className="mt-1 text-sm font-medium text-slate-800">Policy-aware scoring plus breach signals</p>
              </div>
            </div>
            
            {error && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4">
                <p className="text-sm font-medium text-red-700">{error}</p>
              </div>
            )}

            <div className="mb-6">
              <label htmlFor="password" className="block text-sm font-medium text-slate-700">
                Password
              </label>
              <div className="relative mt-2 rounded-lg shadow-sm">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="block w-full rounded-lg border border-slate-300 bg-white px-4 py-3 pr-20 text-sm text-slate-900 outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20"
                  placeholder="Enter a password to test"
                />
                <button
                  type="button"
                  className="absolute inset-y-0 right-0 flex items-center pr-4 text-sm font-semibold text-slate-600 transition-colors hover:text-teal-700 focus:outline-none"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? "Hide" : "Show"}
                </button>
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={handleScore}
                disabled={isLoading}
                className="inline-flex items-center justify-center rounded-lg bg-teal-600 px-6 py-3 text-sm font-semibold text-white shadow-md transition-all duration-200 hover:-translate-y-0.5 hover:bg-teal-700 hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 disabled:opacity-50"
              >
                {isLoading ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                    </svg>
                    Analyzing...
                  </>
                ) : (
                  "Analyze Password"
                )}
              </button>
              <button
                type="button"
                onClick={handleClear}
                disabled={isLoading}
                className="inline-flex justify-center rounded-lg border border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-700 shadow-sm transition-all duration-200 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 disabled:opacity-50"
              >
                Clear
              </button>
            </div>
          </div>
          
          {result && (
            <div className="animate-in slide-in-from-bottom-4 fade-in border-t border-slate-200 bg-slate-50/70 p-6 duration-500 sm:p-8">
               <PasswordResult result={result} />
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
