import { Suspense } from "react";
import { AgentRunsList } from "@/components/runs/AgentRunsList";

export default function RunsPage() {
  return (
    <Suspense fallback={<p>Loading agent runs…</p>}>
      <AgentRunsList />
    </Suspense>
  );
}
