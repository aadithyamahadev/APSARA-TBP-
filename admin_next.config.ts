import { fileURLToPath } from "node:url";

import type { NextConfig } from "next";

const turbopackRoot = fileURLToPath(new URL(".", import.meta.url));

const nextConfig: NextConfig = {
  turbopack: {
    root: turbopackRoot,
  },
};

export default nextConfig;
