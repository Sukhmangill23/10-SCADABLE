import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { isClerkConfigured } from "@/lib/auth/config";

export default async function HomePage() {
  if (!isClerkConfigured()) {
    redirect("/competitors");
  }

  const { userId } = await auth();

  if (!userId) {
    redirect("/sign-up");
  }

  redirect("/competitors");
}
