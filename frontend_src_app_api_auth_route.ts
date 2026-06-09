import { NextResponse } from 'next/server';
import { getApiBaseUrl } from '@/lib/api-base-url';

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

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { action, email, password } = body; // action: 'login' | 'register'

    if (!action || !email || !password) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }

    const isLogin = action === 'login';

    if (!isLogin && action !== 'register') {
      return NextResponse.json({ error: 'Invalid action' }, { status: 400 });
    }

    const endpoint = isLogin ? '/auth/login' : '/auth/register';

    const candidateBaseUrls = buildCandidateBaseUrls();
    let response: Response | null = null;
    let lastNetworkError: unknown;

    for (const baseUrl of candidateBaseUrls) {
      try {
        response = await fetch(`${baseUrl}${endpoint}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ email, password }),
        });
        break;
      } catch (networkError) {
        lastNetworkError = networkError;
      }
    }

    if (response === null) {
      console.error('Auth upstream unavailable:', lastNetworkError);
      return NextResponse.json(
        { error: 'Auth service is unavailable. Start API/Nginx and try again.' },
        { status: 502 }
      );
    }

    if (!response.ok) {
      let errorMessage = 'Authentication failed';
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorData.message || errorMessage;
      } catch {
        const fallbackText = await response.text();
        if (fallbackText) {
          errorMessage = fallbackText;
        }
      }
      return NextResponse.json({ error: errorMessage }, { status: response.status });
    }

    const data = await response.json();
    const token = data.access_token;

    if (!token) {
      return NextResponse.json({ error: 'No token received from backend' }, { status: 400 });
    }

    const res = NextResponse.json({ success: true });
    res.cookies.set('auth_token', token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      path: '/',
      maxAge: 60 * 60 * 24 * 7,
    });

    return res;
  } catch (error) {
    console.error('Auth API route error:', error);
    return NextResponse.json({ error: 'Unexpected auth gateway error' }, { status: 500 });
  }
}
