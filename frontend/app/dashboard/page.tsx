import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { DashboardClient } from "@/components/workspace/DashboardClient";

export default async function DashboardPage() {
  const supabase = await createClient();
  if (!supabase) redirect("/signin");
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/signin");
  return <DashboardClient />;
}
