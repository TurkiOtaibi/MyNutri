import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

const PUBLIC_AUTH_PATHS = ["/auth/login", "/auth/sign-up", "/auth/forgot-password"];

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
  const authenticated = Boolean(data?.claims?.sub);
  const path = request.nextUrl.pathname;
  const publicAuth = PUBLIC_AUTH_PATHS.includes(path);

  if (!authenticated && !publicAuth && path !== "/auth/reset-password") {
    const redirect = request.nextUrl.clone();
    redirect.pathname = "/auth/login";
    redirect.searchParams.set("next", path);
    return NextResponse.redirect(redirect);
  }
  if (authenticated && publicAuth) {
    return NextResponse.redirect(new URL("/diary", request.url));
  }
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|manifest.json|service-worker.js|icon.svg).*)"]
};
