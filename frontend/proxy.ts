import { NextResponse } from "next/server";

// Bearer tokens are browser-owned, never cookies. AuthProvider gates rendering;
// FastAPI authorizes every private read and write.
export function proxy() {
  return NextResponse.next();
}
export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|manifest.json|service-worker.js|icon.svg).*)"]
};
