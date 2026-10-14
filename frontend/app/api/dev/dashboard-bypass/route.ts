import { NextResponse } from "next/server";
import {
  DEV_DASHBOARD_BYPASS_COOKIE,
  isDevDashboardBypassAllowed,
} from "@/lib/auth/bypass";

export async function GET(request: Request) {
  const url = new URL("/overview", request.url);

  if (!isDevDashboardBypassAllowed()) {
    return NextResponse.redirect(new URL("/sign-up", request.url));
  }

  const response = NextResponse.redirect(url);
  response.cookies.set(DEV_DASHBOARD_BYPASS_COOKIE, "1", {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24 * 7,
  });

  return response;
}
