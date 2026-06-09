"use client";

export type ResultType = {
  score: number;
  risk_label: string;
  strength_label: string;
  crack_time_display: string;
  is_breached: boolean;
  breach_count: number;
  patterns_detected: string[];
  recommendations: string[];
};

export default function PasswordResult({ result }: { result: ResultType }) {
  const {
    score,
    risk_label,
    strength_label,
    crack_time_display,
    is_breached,
    breach_count,
    patterns_detected,
    recommendations,
  } = result;

  const getScoreStyle = (src: number) => {
    if (src < 40) {
      return { barClass: "bg-red-500", textClass: "text-red-600", ringHex: "#ef4444" };
    }
    if (src < 70) {
      return { barClass: "bg-orange-500", textClass: "text-orange-600", ringHex: "#f97316" };
    }
    if (src < 90) {
      return { barClass: "bg-amber-400", textClass: "text-amber-600", ringHex: "#f59e0b" };
    }
    return { barClass: "bg-emerald-500", textClass: "text-emerald-600", ringHex: "#10b981" };
  };

  const scoreStyle = getScoreStyle(score);
  const safeScore = Math.max(0, Math.min(100, score));
  const gaugeStyle = {
    background: `conic-gradient(${scoreStyle.ringHex} ${safeScore * 3.6}deg, #e2e8f0 ${safeScore * 3.6}deg)`,
  };

  return (
    <div className="mt-2 space-y-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex flex-col md:flex-row items-center justify-between gap-6 pb-6 border-b border-slate-100">
        <div className="flex-1 w-full text-center md:text-left">
          <h3 className="text-xl font-semibold text-slate-900 mb-2">Password Strength</h3>
          <p className="text-slate-600 capitalize">{strength_label} • {risk_label} Risk</p>
          <div className="mt-5 flex items-center gap-4">
            <span className="text-sm font-medium text-slate-700 w-16">Score</span>
            <div className="flex-1 max-w-sm h-3 bg-slate-200 rounded-full overflow-hidden">
              <div className={`h-full ${scoreStyle.barClass} transition-all duration-1000 ease-out`} style={{ width: `${safeScore}%` }} />
            </div>
            <span className={`text-sm font-bold ${scoreStyle.textClass}`}>{safeScore}/100</span>
          </div>
        </div>

        <div className="flex items-center gap-4 rounded-xl border border-slate-200 bg-slate-50 p-4 shadow-sm">
          <div className="relative h-20 w-20 rounded-full p-[6px] transition-all duration-700" style={gaugeStyle}>
            <div className="flex h-full w-full items-center justify-center rounded-full bg-white">
              <span className={`text-sm font-bold ${scoreStyle.textClass}`}>{safeScore}</span>
            </div>
          </div>
          <div className="text-left">
            <p className="text-xs font-semibold uppercase text-slate-400">Estimated Crack Time</p>
            <p className="mt-1 text-base font-bold text-slate-800">{crack_time_display}</p>
          </div>
        </div>
      </div>

      {is_breached && (
        <div className="bg-red-50 border-l-4 border-red-500 p-5 rounded-r-md animate-in slide-in-from-left-2 duration-300">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-6 w-6 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-md font-bold text-red-800 uppercase tracking-wide">Data Breach Detected!</h3>
              <p className="text-sm text-red-700 mt-1">
                This password has appeared in <span className="font-bold">{breach_count}</span> known data breaches. Do not use it.
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div>
          <h4 className="text-sm font-semibold text-slate-900 uppercase tracking-wider mb-4 border-b pb-2">Patterns Detected</h4>
          {patterns_detected && patterns_detected.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {patterns_detected.map((pattern, idx) => (
                <span key={idx} className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-800 border border-orange-200 transition-transform hover:-translate-y-0.5">
                  {pattern}
                </span>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500 italic">No concerning patterns found.</p>
          )}
        </div>

        <div>
           <h4 className="text-sm font-semibold text-slate-900 uppercase tracking-wider mb-4 border-b pb-2">Recommendations</h4>
          {recommendations && recommendations.length > 0 ? (
            <ul className="space-y-3">
              {recommendations.map((rec, idx) => (
                <li key={idx} className="flex items-start">
                  <span className="flex-shrink-0 h-5 w-5 bg-teal-100 text-teal-700 rounded-full flex items-center justify-center mr-3 mt-0.5">
                    <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </span>
                  <span className="text-sm text-slate-600">{rec}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500 italic">None. Keep up the good work!</p>
          )}
        </div>
      </div>
    </div>
  );
}
