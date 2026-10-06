"use client";

import Link from "next/link";
import { useState } from "react";

export function AuraDocHeader() {
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);

  return (
    <header className="site-header" id="top">
      <Link className="brand" href="/" aria-label="AuraDoc home"><span className="brand-mark" aria-hidden="true"><span /><span /><span /></span><span>Aura<span className="brand-accent">Doc</span></span></Link>
      <nav id="primary-navigation" className={`nav${open ? " mobile-open" : ""}`} aria-label="Primary navigation">
        <a href="#capabilities" onClick={close}>Capabilities</a><a href="#workflow" onClick={close}>Workflow</a><a href="#security" onClick={close}>Security</a><a href="#about" onClick={close}>About</a>
      </nav>
      <div className="header-actions"><Link className="text-link" href="/signin">Sign in</Link><Link className="button button-small" href="/signup">Request access <span>↗</span></Link></div>
      <button className="menu-button" type="button" aria-label={open ? "Close menu" : "Open menu"} aria-expanded={open} aria-controls="primary-navigation" onClick={() => setOpen(!open)}>☰</button>
    </header>
  );
}
