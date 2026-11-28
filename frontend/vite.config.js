import { defineConfig } from "vite";

// Use React's automatic JSX runtime so components do not need `import React`.
export default defineConfig({
  esbuild: { jsx: "automatic" },
});
