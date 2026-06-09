import { NextRequest, NextResponse } from "next/server";

import { getApiBaseUrl } from "@/lib/api-base-url";


export async function POST(request: NextRequest) {
  try {
    const API_URL = getApiBaseUrl();
    let body: unknown;
    try {
      body = await request.json();
    } catch {
      return NextResponse.json(
        { detail: "Invalid JSON payload" },
        { status: 400 }
      );
    }

    const response = await fetch(`${API_URL}/admin/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    const contentType = response.headers.get("content-type") || "";
    const data = contentType.includes("application/json")
      ? await response.json()
      : { detail: await response.text() };

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    // Create response and set auth cookie
    const res = NextResponse.json(data);
    if (data.access_token) {
      res.cookies.set("auth_token", data.access_token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        maxAge: data.expires_in || 3600,
      });
    }

    return res;
  } catch (error) {
    console.error("Admin auth gateway error:", error);
    return NextResponse.json(
      { detail: "Internal server error" },
      { status: 500 }
    );
  }
}
