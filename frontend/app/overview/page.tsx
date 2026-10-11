import { PlaceholderPanel } from "@/components/ui/PlaceholderPanel";

export default function OverviewPage() {
  return (
    <PlaceholderPanel
      title="SWOT Overview"
      owner="FE B"
      description="Four-quadrant SWOT across all competitors. Each item links to competitor + source. Wire to swotApi.getSwotOverview()."
    />
  );
}
