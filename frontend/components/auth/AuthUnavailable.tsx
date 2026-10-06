import Link from "next/link";

type AuthUnavailableProps = { title: string; description: string };

export function AuthUnavailable({ title, description }: AuthUnavailableProps) {
  return (
    <main className="auth-page">
      <section className="auth-panel">
        <Link className="brand" href="/"><span className="brand-mark" aria-hidden="true"><span /><span /><span /></span><span>Aura<span className="brand-accent">Doc</span></span></Link>
        <p className="section-label">PRIVATE FORENSIC WORKBENCH</p>
        <h1>{title}</h1>
        <p>{description}</p>
        <div className="auth-notice" role="status">Authentication is not connected yet. No account, session, or password reset will be created by this foundation.</div>
        <Link className="button" href="/">Return to AuraDoc <span>→</span></Link>
        <nav className="auth-links" aria-label="Account routes"><Link href="/signin">Sign in</Link><Link href="/signup">Request access</Link><Link href="/forgot-password">Forgot password</Link></nav>
      </section>
      <aside className="auth-aside"><span>CONTROLLED ACCESS</span><strong>Your evidence.<br />Your judgment.</strong><small>Authentication service integration is a future implementation phase.</small></aside>
    </main>
  );
}
