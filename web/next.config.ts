import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Fully static site: all data is committed JSON read at build time, so the
  // dashboard exports to plain HTML/JS in web/out — deployable on any static
  // host and immune to Vercel framework auto-detection at the repo root.
  output: "export",
};

export default nextConfig;
