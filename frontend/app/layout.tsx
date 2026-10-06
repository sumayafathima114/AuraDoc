import type { Metadata } from "next";
import "./globals.css";
import "./landing.css";
import "./workspace.css";
import "./legal-workflow.css";

export const metadata: Metadata = {
  title: "AuraDoc — Forensic Audio & Legal Document Review",
  description:
    "A privacy-first workbench for connecting recorded statements with traceable source-document evidence for human review.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
