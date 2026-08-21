import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Pages that require authentication — redirect to /login if no session cookie
const PROTECTED_PATHS = ["/account", "/workspace", "/reports", "/watchlist"];

// Pages that should redirect to /dashboard if already signed in
const GUEST_ONLY_PATHS = ["/login", "/register"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const sessionCookie = request.cookies.get("statlas_session");

  // Redirect protected pages to /login if not authenticated
  if (PROTECTED_PATHS.some((p) => pathname === p || pathname.startsWith(p + "/"))) {
    if (!sessionCookie) {
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("redirect", pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  // Redirect login/register to /dashboard if already authenticated
  if (GUEST_ONLY_PATHS.some((p) => pathname === p || pathname.startsWith(p + "/"))) {
    if (sessionCookie) {
      return NextResponse.redirect(new URL("/dashboard", request.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/account/:path*",
    "/workspace/:path*",
    "/reports/:path*",
    "/watchlist/:path*",
    "/login",
    "/register",
  ],
};
