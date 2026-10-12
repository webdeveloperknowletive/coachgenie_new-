import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { jwtVerify, type JWTPayload } from "jose";

const BACKEND = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

const ACCESS_TOKEN_MAX_AGE = 60 * 60 * 24;        // 24 hours
const REFRESH_TOKEN_MAX_AGE = 60 * 60 * 24 * 30; // 30 days

const PUBLIC_PATHS = [
  "/login",
  "/forgot-password",
  "/verify-otp",
  "/reset-password",
  "/api/auth",
  "/api/chat",
  "/offline",
  "/sw.js",
  "/manifest.webmanifest",
  "/manifest.json",
];

function getSecret(): Uint8Array {
  const secret = process.env.SECRET_KEY;

  if (!secret) {
    console.error(
      "[middleware] SECRET_KEY is not set — all protected routes denied"
    );
    return new Uint8Array(0);
  }

  return new TextEncoder().encode(secret);
}

interface CgTokenPayload extends JWTPayload {
  sub: string;
  tenant_id: string;
  role: string;
}

async function verifyToken(token: string): Promise<CgTokenPayload | null> {
  try {
    const secret = getSecret();
    if (!secret.length) return null;

    const { payload } = await jwtVerify(token, secret);
    return payload as CgTokenPayload;
  } catch {
    return null;
  }
}

async function tryRefreshTokens(refreshToken: string) {
  try {
    const res = await fetch(`${BACKEND}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return null;
    return (await res.json()) as { access_token: string; refresh_token: string };
  } catch {
    return null;
  }
}

export async function middleware(request: NextRequest) {
  const token = request.cookies.get("cg_access_token")?.value;
  const refreshToken = request.cookies.get("cg_refresh_token")?.value;
  const pathname = request.nextUrl.pathname;
  const isPublic = PUBLIC_PATHS.some((p) => pathname.startsWith(p));

  let payload: CgTokenPayload | null = null;
  let newTokens: { access_token: string; refresh_token: string } | null = null;

  if (token) {
    payload = await verifyToken(token);
  }

  // If access token is invalid/expired or missing, try refreshing with refresh token
  if (!payload && refreshToken) {
    newTokens = await tryRefreshTokens(refreshToken);
    if (newTokens) {
      payload = await verifyToken(newTokens.access_token);
    }
  }

  // Authenticated user hitting /login → redirect to dashboard
  if (payload && pathname.startsWith("/login")) {
    const url = request.nextUrl.clone();
    url.pathname = "/dashboard";
    url.search = "";

    const response = NextResponse.redirect(url);
    if (newTokens) {
      response.cookies.set("cg_access_token", newTokens.access_token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "strict",
        path: "/",
        maxAge: ACCESS_TOKEN_MAX_AGE,
      });
      response.cookies.set("cg_refresh_token", newTokens.refresh_token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "strict",
        path: "/",
        maxAge: REFRESH_TOKEN_MAX_AGE,
      });
    }
    return response;
  }

  // Unauthenticated user hitting a protected route
  if (!payload && !isPublic) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    if (token || refreshToken) {
      url.searchParams.set("reason", "session_expired");
    }

    const response = NextResponse.redirect(url);
    response.cookies.set("cg_access_token", "", {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "strict",
      path: "/",
      maxAge: 0,
    });
    response.cookies.set("cg_refresh_token", "", {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "strict",
      path: "/",
      maxAge: 0,
    });

    return response;
  }

  // Token valid on protected route — inject user/tenant headers
  if (payload && !isPublic) {
    const requestHeaders = new Headers(request.headers);
    requestHeaders.set("x-user-id", payload.sub);
    requestHeaders.set(
      "x-tenant-id",
      payload.tenant_id ?? (payload as any).tenantId
    );
    requestHeaders.set("x-user-role", payload.role);

    const response = NextResponse.next({
      request: {
        headers: requestHeaders,
      },
    });

    if (newTokens) {
      response.cookies.set("cg_access_token", newTokens.access_token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "strict",
        path: "/",
        maxAge: ACCESS_TOKEN_MAX_AGE,
      });
      response.cookies.set("cg_refresh_token", newTokens.refresh_token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "strict",
        path: "/",
        maxAge: REFRESH_TOKEN_MAX_AGE,
      });
    }

    return response;
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|icons|images|sw.js|manifest.webmanifest|manifest.json).*)"],
};