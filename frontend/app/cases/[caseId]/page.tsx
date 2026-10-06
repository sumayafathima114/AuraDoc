import { notFound, redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { WorkbenchClient } from "@/components/cases/WorkbenchClient";
export default async function CasePage({ params }: { params: Promise<{ caseId: string }> }) { const supabase = await createClient(); if (!supabase) redirect("/signin"); const { data: { user } } = await supabase.auth.getUser(); if (!user) redirect("/signin"); const { caseId } = await params; if (!/^[0-9a-f-]{36}$/i.test(caseId)) notFound(); return <WorkbenchClient caseId={caseId} />; }
