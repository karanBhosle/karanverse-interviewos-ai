import { ReportView } from "./report-view";

export default async function ReportPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = await params;
  return <ReportView sessionId={sessionId} />;
}
