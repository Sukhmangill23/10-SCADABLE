import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse, type NextRequest } from "next/server";
import {
  DEV_DASHBOARD_BYPASS_COOKIE,
  isDevDashboardBypassAllowed,
} from "@/lib/auth/bypass";

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

const withClerk = clerkMiddleware(async (auth, request) => {
  if (isPublicRoute(request) || hasDevDashboardBypass(request)) {
    return;
  }

  await auth.protect({
    unauthenticatedUrl: new URL("/sign-up", request.url).toString(),
  });
});

function passthrough(_request: NextRequest) {
  return NextResponse.next();
}

export default clerkEnabled ? withClerk : passthrough;

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
