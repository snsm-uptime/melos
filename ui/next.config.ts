import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  experimental: {
    // Picture capture posts a base64 body up to ~13 MB (spec 041, FR-024, research R11).
    proxyClientMaxBodySize: "14mb",
  },
};

export default nextConfig;
