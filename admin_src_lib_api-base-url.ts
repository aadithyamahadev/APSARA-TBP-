export function getApiBaseUrl() {
  const configuredUrl = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL;

  if (configuredUrl && configuredUrl.trim()) {
    return configuredUrl.trim().replace(/\/$/, "");
  }

  if (process.env.NODE_ENV !== "production") {
    return "http://localhost:8000";
  }

  throw new Error(
    "API_URL or NEXT_PUBLIC_API_URL must be configured in production for the APSARA frontend to reach the backend."
  );
}