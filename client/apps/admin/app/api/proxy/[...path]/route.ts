import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

const ACCESS_TOKEN_MAX_AGE  = 60 * 60 * 24;        // 24 hours
const REFRESH_TOKEN_MAX_AGE = 60 * 60 * 24 * 30; // 30 days

async function refreshBackendTokens(refreshToken: string) {
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

async function handler(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const cookieStore = await cookies();
  let token = cookieStore.get("cg_access_token")?.value;
  const refreshToken = cookieStore.get("cg_refresh_token")?.value;

  // Middleware already verified the JWT and injected headers
  const tenantId = request.headers.get("x-tenant-id");
  const userRole = request.headers.get("x-user-role");

  const { path } = await params;
  const isPlatformRoute = path.length > 0 && path[0] === "platform";

  if (!tenantId || tenantId === "undefined" || tenantId === "null") {
    if (userRole !== "super_admin" && !isPlatformRoute) {
      return NextResponse.json({ error: "Missing tenant context" }, { status: 401 });
    }
  }

  const search = request.nextUrl.search;
  const url = `${BACKEND}/${path.join("/")}${search}`;
  const rawBody = !["GET", "DELETE", "HEAD"].includes(request.method)
    ? await request.text()
    : undefined;

  let newTokens: { access_token: string; refresh_token: string } | null = null;

  // If access token is missing but refresh token exists, refresh first
  if (!token && refreshToken) {
    newTokens = await refreshBackendTokens(refreshToken);
    if (newTokens) {
      token = newTokens.access_token;
    }
  }

  if (!token) {
    const response = NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    response.cookies.set("cg_access_token", "", { httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "strict", path: "/", maxAge: 0 });
    response.cookies.set("cg_refresh_token", "", { httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "strict", path: "/", maxAge: 0 });
    return response;
  }

  const headers: HeadersInit = {
    "Content-Type":  "application/json",
    "Authorization": `Bearer ${token}`,
  };

  if (tenantId && tenantId !== "undefined" && tenantId !== "null") {
    (headers as Record<string, string>)["X-Tenant-Id"] = tenantId;
  }

  const init: RequestInit = { method: request.method, headers };
  if (rawBody !== undefined) {
    init.body = rawBody;
  }

  let res: Response;
  try {
    res = await fetch(url, init);
  } catch (err) {
    return NextResponse.json(
      { error: "Backend service temporarily unavailable. Please verify the backend is running." },
      { status: 503 }
    );
  }

  // If backend returns 401 (token expired), try refreshing and retrying
  if (res.status === 401 && refreshToken && !newTokens) {
    newTokens = await refreshBackendTokens(refreshToken);
    if (newTokens) {
      const retryHeaders: HeadersInit = {
        "Content-Type":  "application/json",
        "Authorization": `Bearer ${newTokens.access_token}`,
      };
      if (tenantId && tenantId !== "undefined" && tenantId !== "null") {
        (retryHeaders as Record<string, string>)["X-Tenant-Id"] = tenantId;
      }
      const retryInit: RequestInit = { method: request.method, headers: retryHeaders };
      if (rawBody !== undefined) {
        retryInit.body = rawBody;
      }
      try {
        res = await fetch(url, retryInit);
      } catch (err) {
        return NextResponse.json(
          { error: "Backend service temporarily unavailable. Please verify the backend is running." },
          { status: 503 }
        );
      }
    }
  }

  const data = await res.text();

  if (res.status === 401) {
    const response = new NextResponse(data, {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
    response.cookies.set("cg_access_token", "", { httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "strict", path: "/", maxAge: 0 });
    response.cookies.set("cg_refresh_token", "", { httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "strict", path: "/", maxAge: 0 });
    return response;
  }

  const response = new NextResponse(data, {
    status: res.status,
    headers: { "Content-Type": "application/json" },
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

export const GET    = handler;
export const POST   = handler;
export const PATCH  = handler;
export const PUT    = handler;
export const DELETE = handler;