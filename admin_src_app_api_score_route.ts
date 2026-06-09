import { NextRequest, NextResponse } from "next/server";
import { getApiBaseUrl } from "@/lib/api-base-url";

function buildCandidateBaseUrls() {
  const configuredUrl = process.env.NEXT_PUBLIC_API_URL || process.env.API_URL;
  return Array.from(
    new Set(
      [
        configuredUrl,
        getApiBaseUrl(),
      ].filter(Boolean)
    )
  ) as string[];
}

export async function POST(req: NextRequest) {
  try {
    const token = req.cookies.get("auth_token")?.value;

    if (!token) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await req.json();
    const { password } = body;

    const candidateBaseUrls = buildCandidateBaseUrls();
    let response: Response | null = null;
    let lastNetworkError: unknown;

    for (const baseUrl of candidateBaseUrls) {
      try {
        response = await fetch(`${baseUrl}/score`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({ password })
        });
        break;
      } catch (networkError) {
        lastNetworkError = networkError;
      }
    }

    if (response === null) {
      console.error("Score upstream unavailable:", lastNetworkError);
      return NextResponse.json(
        { error: "Scoring service is unavailable. Start API/Nginx and try again." },
        { status: 502 }
      );
    }

    if (response.status === 401) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json({ error: "Unexpected score gateway error" }, { status: 500 });
  }
}