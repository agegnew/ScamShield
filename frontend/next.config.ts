import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Everything reads live from the ScamShield API in the browser, so we keep
  // rendering simple and dynamic rather than opting into component caching.
  cacheComponents: false,
  partialPrefetching: false,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
