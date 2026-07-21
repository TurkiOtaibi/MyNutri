import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

const PUBLIC_AUTH_PATHS = ["/auth/login", "/auth/sign-up", "/auth/forgot-password"];
const INVALID_TOKEN_COOKIE = "mynutri-auth-invalid-token";
const TOKEN_FINGERPRINT = /^[0-9a-f]{64}$/;

function clearInvalidToken(response: NextResponse) {
  response.cookies.set(INVALID_TOKEN_COOKIE, "", { path: "/", maxAge: 0, sameSite: "lax" });
}

function redirectWithCookies(url: URL, response: NextResponse) {
  const redirect = NextResponse.redirect(url);
  response.cookies.getAll().forEach((cookie) => redirect.cookies.set(cookie));
  return redirect;
}

async function fingerprint(token: string) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(token));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

export async function proxy(request: NextRequest) {
  let response = NextResponse.next({ request });
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  if (!url || !key) {
    return new NextResponse("Authentication configuration unavailable", { status: 503 });
  }

  const supabase = createServerClient(url.replace(/\/+$/, ""), key, {
    cookies: {
      getAll: () => request.cookies.getAll(),
      setAll: (items) => {
        items.forEach(({ name, value }) => request.cookies.set(name, value));
        response = NextResponse.next({ request });
        items.forEach(({ name, value, options }) => response.cookies.set(name, value, options));
      }
    }
  });
  const { data } = await supabase.auth.getClaims();
  const subject = typeof data?.claims?.sub === "string" ? data.claims.sub : null;
  const marker = request.cookies.get(INVALID_TOKEN_COOKIE)?.value;
  let authenticated = Boolean(subject);
  if (marker && TOKEN_FINGERPRINT.test(marker)) {
    const { data: sessionData } = await supabase.auth.getSession();
    const currentToken = sessionData.session?.access_token;
    if (currentToken && marker === await fingerprint(currentToken)) authenticated = false;
    clearInvalidToken(response);
  } else if (marker) {
    clearInvalidToken(response);
  }
  const path = request.nextUrl.pathname;
  const publicAuth = PUBLIC_AUTH_PATHS.includes(path);

  if (!authenticated && !publicAuth && path !== "/auth/reset-password") {
    const redirect = request.nextUrl.clone();
    redirect.pathname = "/auth/login";
    redirect.searchParams.set("next", `${path}${request.nextUrl.search}`);
    return redirectWithCookies(redirect, response);
  }
  if (authenticated && publicAuth) {
    return redirectWithCookies(new URL("/diary", request.url), response);
  }
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|manifest.json|service-worker.js|icon.svg).*)"]
};
