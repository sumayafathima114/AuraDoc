import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { SettingsClient } from "@/components/workspace/SettingsClient";

export default async function SettingsPage() {
  const supabase = await createClient();
  if (!supabase) redirect("/signin");
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/signin");
  return <SettingsClient />;
}
