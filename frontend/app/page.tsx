import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { isClerkConfigured } from "@/lib/auth/config";

export default async function HomePage() {
  if (!isClerkConfigured()) {
    redirect("/overview");
  }

  const { userId } = await auth();

  if (!userId) {
    redirect("/sign-in");
  }

  redirect("/overview");
}
