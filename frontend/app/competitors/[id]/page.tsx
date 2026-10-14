import { CompetitorProfileView } from "@/components/competitors/CompetitorProfileView";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function CompetitorProfilePage({ params }: Props) {
  const { id } = await params;
  return <CompetitorProfileView id={id} />;
}
