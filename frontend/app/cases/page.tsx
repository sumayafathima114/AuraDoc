import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { CasesClient } from "@/components/cases/CasesClient";
export default async function CasesPage() { const supabase = await createClient(); if (!supabase) redirect("/signin"); const { data: { user } } = await supabase.auth.getUser(); if (!user) redirect("/signin"); return <CasesClient />; }
