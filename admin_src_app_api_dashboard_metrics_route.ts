import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

import { getApiBaseUrl } from "@/lib/api-base-url";


export async function GET(request: NextRequest) {
  try {
    const API_URL = getApiBaseUrl();
    const cookieStore = await cookies();
    const token = cookieStore.get("auth_token")?.value;

    if (!token) {
      return NextResponse.json(
        { detail: "Unauthorized" },
        { status: 401 }
      );
    }

    const response = await fetch(`${API_URL}/admin/dashboard/metrics`, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });

    if (response.status === 401) {
      return NextResponse.json(
        { detail: "Unauthorized" },
        { status: 401 }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Admin metrics gateway error:", error);
    return NextResponse.json(
      { detail: "Internal server error" },
      { status: 500 }
    );
  }
}
