import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

const PUBLIC_AUTH_PATHS = ["/auth/login", "/auth/sign-up", "/auth/forgot-password"];
const INVALID_SUBJECT_COOKIE = "mynutri-auth-invalid-subject";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function clearInvalidSubject(response: NextResponse) {
  response.cookies.set(INVALID_SUBJECT_COOKIE, "", { path: "/", maxAge: 0, sameSite: "lax" });
}

function redirectWithCookies(url: URL, response: NextResponse) {
  const redirect = NextResponse.redirect(url);
  response.cookies.getAll().forEach((cookie) => redirect.cookies.set(cookie));
  return redirect;
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
  const marker = request.cookies.get(INVALID_SUBJECT_COOKIE)?.value;
  if (marker && UUID.test(marker)) {
    if (marker === subject) {
      await supabase.auth.signOut();
      const redirect = redirectWithCookies(new URL("/auth/login", request.url), response);
      clearInvalidSubject(redirect);
      return redirect;
    }
    clearInvalidSubject(response);
  } else if (marker) {
    clearInvalidSubject(response);
  }
  const authenticated = Boolean(subject);
  const path = request.nextUrl.pathname;
  const publicAuth = PUBLIC_AUTH_PATHS.includes(path);

  if (!authenticated && !publicAuth && path !== "/auth/reset-password") {
    const redirect = request.nextUrl.clone();
    redirect.pathname = "/auth/login";
    redirect.searchParams.set("next", path);
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
