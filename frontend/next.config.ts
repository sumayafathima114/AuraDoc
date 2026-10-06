import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  poweredByHeader: false,
  // Root and frontend lockfiles are intentional: root owns the Supabase CLI,
  // while frontend owns the Next.js app and its independent dependency tree.
  turbopack: { root: process.cwd() },
};

export default nextConfig;
