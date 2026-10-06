import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { ProfileClient } from "@/components/workspace/ProfileClient";

export default async function ProfilePage() {
  const supabase = await createClient();
  if (!supabase) redirect("/signin");
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/signin");
  return <ProfileClient />;
}
