import { redirect } from "next/navigation";

export default async function LeagueHub({ params }: { params: Promise<{ leagueCode: string }> }) {
  const { leagueCode } = await params;
  redirect(`/leagues/${leagueCode}/stats`);
}
