"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { WorkspaceShell } from "@/components/workspace/WorkspaceShell";

type Theme = "light" | "dark" | "system";

export function SettingsClient() {
  const [theme, setTheme] = useState<Theme>("system");
  useEffect(() => {
    const saved = localStorage.getItem("auradoc-theme");
    if (saved === "light" || saved === "dark" || saved === "system") setTheme(saved);
  }, []);
  function updateTheme(value: Theme) {
    setTheme(value);
    localStorage.setItem("auradoc-theme", value);
    window.dispatchEvent(new CustomEvent("auradoc-theme-change", { detail: value }));
  }
  return <WorkspaceShell active="/settings">
    <div className="ad-page-heading"><div><p className="ad-eyebrow">PREFERENCES & ACCOUNT</p><h1>Settings</h1><p className="ad-lead">Manage local display preferences and account access.</p></div></div>
    <section className="ad-panel ad-settings-panel"><p className="ad-eyebrow">APPEARANCE</p><h2>Workspace theme</h2><p className="ad-body-copy">This preference is stored in this browser. It does not change evidence or account data.</p><label htmlFor="settings-theme">Theme</label><select id="settings-theme" value={theme} onChange={(event) => updateTheme(event.target.value as Theme)}><option value="system">System</option><option value="light">Light</option><option value="dark">Dark</option></select></section>
    <section className="ad-panel ad-settings-panel"><p className="ad-eyebrow">ACCOUNT SECURITY</p><h2>Password and profile</h2><p className="ad-body-copy">Password changes are handled by your configured Supabase Auth flow. Profile data remains scoped to your authenticated account.</p><div className="ad-settings-links"><Link href="/forgot-password">Request a password reset →</Link><Link href="/profile">Manage display name →</Link></div></section>
    <section className="ad-panel ad-settings-panel"><p className="ad-eyebrow">NOT CONFIGURED</p><h2>Notifications and retention</h2><p className="ad-body-copy">Notification preferences and data-retention controls are not implemented yet. No preference is implied or changed here.</p></section>
  </WorkspaceShell>;
}
