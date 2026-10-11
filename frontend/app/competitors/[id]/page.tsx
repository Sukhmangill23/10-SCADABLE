import { PlaceholderPanel } from "@/components/ui/PlaceholderPanel";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function CompetitorProfilePage({ params }: Props) {
  const { id } = await params;

  return (
    <PlaceholderPanel
      title={`Competitor profile · ${id}`}
      owner="FE A"
      description="Findings with source links, change badges, and Recharts graphs. Wire to competitorsApi.getCompetitor(id)."
    />
  );
}
