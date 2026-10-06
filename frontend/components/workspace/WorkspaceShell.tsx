"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/browser";

const nav = [
  ["Overview", "/dashboard", "01"], ["Cases", "/cases", "02"],
  ["Legal Intelligence", "/legal-intelligence", "03"], ["Profile", "/profile", "04"],
  ["Settings", "/settings", "05"],
] as const;

export function WorkspaceShell({ children, active }: { children: React.ReactNode; active: string }) {
  const [theme, setTheme] = useState<"light" | "dark" | "system">("system");
  const [email, setEmail] = useState("");
  const [signOutBusy, setSignOutBusy] = useState(false);
  const [signOutError, setSignOutError] = useState("");
  useEffect(() => {
    const saved = localStorage.getItem("auradoc-theme");
    if (saved === "light" || saved === "dark" || saved === "system") setTheme(saved);
    const handleThemeChange = (event: Event) => {
      const value = (event as CustomEvent<unknown>).detail;
      if (value === "light" || value === "dark" || value === "system") setTheme(value);
    };
    window.addEventListener("auradoc-theme-change", handleThemeChange);
    void createClient().auth.getUser().then(({ data }) => setEmail(data.user?.email ?? ""));
    return () => window.removeEventListener("auradoc-theme-change", handleThemeChange);
  }, []);
  useEffect(() => {
    localStorage.setItem("auradoc-theme", theme);
    const preference = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      const dark = theme === "dark" || (theme === "system" && preference.matches);
      document.documentElement.dataset.auradocTheme = dark ? "dark" : "light";
    };
    apply();
    preference.addEventListener("change", apply);
    return () => preference.removeEventListener("change", apply);
  }, [theme]);
  async function signOut() {
    setSignOutBusy(true); setSignOutError("");
    try {
      const { error } = await createClient().auth.signOut();
      if (error) throw error;
      location.assign("/");
    } catch {
      setSignOutError("Sign out failed. Check your connection and try again.");
      setSignOutBusy(false);
    }
  }
  return <div className="ad-workspace">
    <aside className="ad-sidebar">
      <Link className="ad-brand" href="/dashboard"><span className="ad-brand-mark">A</span><span>AuraDoc<small>Evidence · Analysis · Legal Intelligence</small></span></Link>
      <p className="ad-nav-label">WORKSPACE</p>
      <nav aria-label="Workspace navigation">{nav.map(([label, href, number]) => <Link key={href} aria-current={active === href ? "page" : undefined} className={`ad-nav-link ${active === href ? "is-active" : ""}`} href={href}><span>{number}</span>{label}</Link>)}</nav>
      <div className="ad-sidebar-bottom"><span className="ad-secure-mark">◈</span><p>Evidence access is governed by your authenticated case membership.</p><button onClick={signOut}>Sign out</button></div>
    </aside>
    <div className="ad-main-column">
      <header className="ad-topbar"><span className="ad-top-caption">FORENSIC EVIDENCE WORKSPACE</span><div className="ad-top-actions"><label className="ad-theme-label" htmlFor="ad-theme">Theme</label><select id="ad-theme" value={theme} onChange={(e) => setTheme(e.target.value as typeof theme)}><option value="system">System</option><option value="light">Light</option><option value="dark">Dark</option></select><span className="ad-user-email" title={email}>{email || "Signed in"}</span><button className="ad-mobile-signout" onClick={signOut} disabled={signOutBusy}>{signOutBusy ? "Signing out…" : "Sign out"}</button></div>{signOutError && <p className="ad-signout-error" role="alert">{signOutError}</p>}</header>
      <main className="ad-page">{children}</main>
    </div>
  </div>;
}
