import { InterviewRoom } from "./room";

export default async function InterviewSessionPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = await params;
  return <InterviewRoom sessionId={sessionId} />;
}
