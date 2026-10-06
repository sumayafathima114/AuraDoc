import { NextResponse, type NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";

const ALLOWED_DESTINATIONS = new Set(["/dashboard", "/reset-password"]);

export async function GET(request: NextRequest) {
  const code = request.nextUrl.searchParams.get("code");
  const requestedNext = request.nextUrl.searchParams.get("next") ?? "/dashboard";
  const next = ALLOWED_DESTINATIONS.has(requestedNext) ? requestedNext : "/dashboard";
  const supabase = await createClient();

  if (!code || !supabase) {
    return NextResponse.redirect(new URL("/signin", request.url));
  }

  const { error } = await supabase.auth.exchangeCodeForSession(code);
  if (error) {
    return NextResponse.redirect(new URL("/signin", request.url));
  }

  return NextResponse.redirect(new URL(next, request.url));
}
