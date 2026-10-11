import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse, type NextRequest } from "next/server";
import {
  DEV_DASHBOARD_BYPASS_COOKIE,
  isDevDashboardBypassAllowed,
} from "@/lib/auth/bypass";
import { hasClerkInviteTicket } from "@/lib/auth/invite";

const clerkEnabled = Boolean(
  process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY?.trim(),
);

const isPublicRoute = createRouteMatcher([
  "/sign-in(.*)",
  "/sign-up(.*)",
  "/api/dev/dashboard-bypass",
]);

function hasDevDashboardBypass(request: NextRequest) {
  return (
    isDevDashboardBypassAllowed() &&
    request.cookies.get(DEV_DASHBOARD_BYPASS_COOKIE)?.value === "1"
  );
}

function isBareSignUp(request: NextRequest) {
  const { pathname, searchParams } = request.nextUrl;
  return pathname.startsWith("/sign-up") && !hasClerkInviteTicket(searchParams);
}

const withClerk = clerkMiddleware(async (auth, request) => {
  // Never show the restricted public sign-up page — invites only via email link
  if (isBareSignUp(request)) {
    return NextResponse.redirect(new URL("/sign-in", request.url));
  }

  if (isPublicRoute(request) || hasDevDashboardBypass(request)) {
    return;
  }

  await auth.protect({
    unauthenticatedUrl: new URL("/sign-in", request.url).toString(),
  });
});

function passthrough(request: NextRequest) {
  if (isBareSignUp(request)) {
    return NextResponse.redirect(new URL("/sign-in", request.url));
  }
  return NextResponse.next();
}

export default clerkEnabled ? withClerk : passthrough;

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
