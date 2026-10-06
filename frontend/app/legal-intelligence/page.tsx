import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { LegalIntelligenceClient } from "@/components/workspace/LegalIntelligenceClient";

export default async function LegalIntelligencePage() {
  const supabase = await createClient();
  if (!supabase) redirect("/signin");
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/signin");
  return <LegalIntelligenceClient />;
}
