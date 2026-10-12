// app/api/auth/refresh/route.ts
// Reads the httpOnly refresh cookie, exchanges it with FastAPI for a new
// access+refresh pair (rotation), and re-sets both cookies. Never exposes
// tokens to the client — mirrors session/route.ts's cookie conventions.

import { cookies , headers } from "next/headers";
import { NextResponse } from "next/server";

const BACKEND = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";



const ACCESS_TOKEN_MAX_AGE  = 60 * 60 * 24;        // 24 hours
const REFRESH_TOKEN_MAX_AGE = 60 * 60 * 24 * 30; // 30 days

export async function POST() {
  console.log("Refresh route reached");
 
  const cookieStore = await cookies();
  const refreshToken = cookieStore.get("cg_refresh_token")?.value;
  const requestHeaders = await headers();
console.log(
  "Incoming x-playwright-fail-refresh:",
  requestHeaders.get("x-playwright-fail-refresh")
);

  console.log(
  "PLAYWRIGHT:",
  process.env.PLAYWRIGHT
);

console.log(
  "Header:",
  process.env.PLAYWRIGHT === "true"
);

  if (!refreshToken) {
    return NextResponse.json({ error: "No refresh token" }, { status: 401 });
  }

//   const backendRes = await fetch(`${BACKEND}/auth/refresh`, {
//     method: "POST",
//     // headers: { "Content-Type": "application/json" },
//     headers: {
//   "Content-Type": "application/json",

//   ...(process.env.PLAYWRIGHT === "true"
//     ? { "x-playwright-fail-refresh": "1" }
//     : {}),
// },
//     body: JSON.stringify({ refresh_token: refreshToken }),
//   });
  let backendRes: Response;
  try {
    backendRes = await fetch(`${BACKEND}/auth/refresh`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-playwright-fail-refresh":
          requestHeaders.get("x-playwright-fail-refresh") ?? "",
      },
      body: JSON.stringify({
        refresh_token: refreshToken,
      }),
    });
  } catch (err) {
    return NextResponse.json(
      { error: "Backend service temporarily unavailable" },
      { status: 503 }
    );
  }

  if (!backendRes.ok) {
    // Refresh token invalid/expired/reused — clear cookies so we don't loop.
    const response = NextResponse.json({ error: "Refresh failed" }, { status: 401 });
    response.cookies.set("cg_access_token", "", { httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "strict", path: "/", maxAge: 0 });
    response.cookies.set("cg_refresh_token", "", { httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "strict", path: "/", maxAge: 0 });
    return response;
  }

  const { access_token, refresh_token } = await backendRes.json();

  const response = NextResponse.json({ ok: true, access_token });

  response.cookies.set("cg_access_token", access_token, {
    httpOnly: true,
    secure:   process.env.NODE_ENV === "production",
    sameSite: "strict",
    path:     "/",
    maxAge:   ACCESS_TOKEN_MAX_AGE,
  });

  response.cookies.set("cg_refresh_token", refresh_token, {
    httpOnly: true,
    secure:   process.env.NODE_ENV === "production",
    sameSite: "strict",
    path:     "/",
    maxAge:   REFRESH_TOKEN_MAX_AGE,
  });

  return response;
}