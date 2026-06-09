"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<{ email?: string; password?: string; general?: string }>({});
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const switchAuthMode = (loginMode: boolean) => {
    setIsLogin(loginMode);
    setErrors({});
  };

  const validate = () => {
    const newErrors: { email?: string; password?: string } = {};
    if (!email || !/^\S+@\S+\.\S+$/.test(email)) {
      newErrors.email = "Please enter a valid email address.";
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

    setIsLoading(true);
    setErrors({});

    try {
      const response = await fetch("/api/auth", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: isLogin ? "login" : "register", email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        setErrors({ general: data.error || "Authentication failed. Please try again." });
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
    <div className="relative min-h-screen overflow-hidden px-4 py-10 sm:px-6 lg:px-8">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_12%_18%,#bbf7d088,transparent_36%),radial-gradient(circle_at_86%_84%,#67e8f988,transparent_42%)]" />
      <div className="pointer-events-none absolute -left-28 top-20 h-72 w-72 rounded-full bg-emerald-200/30 blur-3xl" />
      <div className="pointer-events-none absolute -right-20 bottom-16 h-64 w-64 rounded-full bg-cyan-200/35 blur-3xl" />

      <div className="relative mx-auto grid w-full max-w-6xl items-center gap-8 lg:grid-cols-2">
        <div className="animate-in fade-in duration-500 lg:pr-6">
          <p className="inline-flex rounded-full border border-teal-200 bg-teal-50 px-3 py-1 text-xs font-semibold tracking-wide text-teal-700">
            APSARA SECURITY PLATFORM
          </p>
          <h1 className="mt-4 text-balance text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl">
            Security that feels as strong as it looks.
          </h1>
          <p className="mt-4 max-w-xl text-sm text-slate-600 sm:text-base">
            {isLogin
              ? "Sign in to continue password intelligence and breach monitoring."
              : "Create your account to start analyzing and hardening credentials."}
          </p>

          <div className="mt-7 grid gap-3 text-sm text-slate-700 sm:grid-cols-2">
            <div className="rounded-xl border border-slate-200/70 bg-white/70 p-4 shadow-sm backdrop-blur">
              <p className="font-semibold text-slate-900">JWT in httpOnly cookie</p>
              <p className="mt-1 text-xs text-slate-600">Tokens stay inaccessible to browser scripts.</p>
            </div>
            <div className="rounded-xl border border-slate-200/70 bg-white/70 p-4 shadow-sm backdrop-blur">
              <p className="font-semibold text-slate-900">Breach-aware scoring</p>
              <p className="mt-1 text-xs text-slate-600">Analyze risk with policy-driven checks.</p>
            </div>
          </div>
        </div>

        <div className="relative mx-auto w-full max-w-md animate-in slide-in-from-bottom-4 fade-in duration-700 lg:mx-0">
        <div className="rounded-2xl border border-slate-200/70 bg-white/90 p-6 shadow-xl backdrop-blur sm:p-8">
          <div className="mb-6 flex rounded-xl bg-slate-100 p-1">
            <button
              type="button"
              onClick={() => switchAuthMode(true)}
              aria-pressed={isLogin}
              className={`w-1/2 rounded-lg px-4 py-2 text-sm font-semibold transition ${
                isLogin
                  ? "bg-white text-slate-900 shadow"
                  : "cursor-pointer text-slate-600 hover:text-slate-900"
              }`}
            >
              Sign in
            </button>
            <button
              type="button"
              onClick={() => switchAuthMode(false)}
              aria-pressed={!isLogin}
              className={`w-1/2 rounded-lg px-4 py-2 text-sm font-semibold transition ${
                !isLogin
                  ? "bg-white text-slate-900 shadow"
                  : "cursor-pointer text-slate-600 hover:text-slate-900"
              }`}
            >
              Register
            </button>
          </div>

          <form className="space-y-6" onSubmit={handleSubmit}>
            {errors.general && (
              <div className="rounded-xl border border-rose-200 bg-rose-50 p-3 animate-in fade-in duration-300">
                <p className="text-sm font-medium text-rose-700">{errors.general}</p>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-slate-700">Email address</label>
              <div className="mt-1">
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={`appearance-none block w-full px-3 py-2 border ${
                    errors.email
                      ? "border-red-300 focus:ring-red-500"
                      : "border-slate-300 focus:ring-teal-500 focus:border-teal-500"
                  } rounded-lg bg-white py-3 text-sm text-slate-900 shadow-sm outline-none transition-colors duration-200`}
                  placeholder="you@company.com"
                />
              </div>
              {errors.email && <p className="mt-2 text-sm text-red-600">{errors.email}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700">Password</label>
              <div className="mt-1">
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={`appearance-none block w-full px-3 py-2 border ${
                    errors.password
                      ? "border-red-300 focus:ring-red-500"
                      : "border-slate-300 focus:ring-teal-500 focus:border-teal-500"
                  } rounded-lg bg-white py-3 text-sm text-slate-900 shadow-sm outline-none transition-colors duration-200`}
                  placeholder="At least 8 characters"
                />
              </div>
              {errors.password && <p className="mt-2 text-sm text-red-600">{errors.password}</p>}
            </div>

            <div>
              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex items-center justify-center rounded-lg bg-teal-600 px-4 py-3 text-sm font-semibold text-white shadow-md transition-all duration-300 ease-out hover:-translate-y-0.5 hover:bg-teal-700 hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 disabled:opacity-50"
              >
                {isLoading ? (
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                  </svg>
                ) : (
                  isLogin ? "Sign in" : "Sign up"
                )}
              </button>
              <p className="mt-3 text-center text-xs text-slate-500">
                Protected session management and secure API routing.
              </p>
              <p className="mt-2 text-center text-sm text-slate-600">
                {isLogin ? "Need an account?" : "Already have an account?"}{" "}
                <button
                  type="button"
                  onClick={() => switchAuthMode(!isLogin)}
                  className="font-semibold text-teal-700 underline-offset-2 hover:underline"
                >
                  {isLogin ? "Register" : "Sign in"}
                </button>
              </p>
            </div>
          </form>
        </div>
      </div>
      </div>
    </div>
  );
}
