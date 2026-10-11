import { PlaceholderPanel } from "@/components/ui/PlaceholderPanel";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function RunDetailPage({ params }: Props) {
  const { id } = await params;

  return (
    <PlaceholderPanel
      title={`Agent run · ${id}`}
      owner="FE A"
      description="Step-by-step run detail. Wire to runsApi.getRun(id)."
    />
  );
}
