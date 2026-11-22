import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The embeddable widget: one self-contained dist/widget.js (React, assistant-ui and the
// compiled CSS, which main.tsx injects into the shadow root).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  define: { "process.env.NODE_ENV": JSON.stringify("production") },
  build: {
    emptyOutDir: false,
    lib: {
      entry: "src/widget/main.tsx",
      formats: ["iife"],
      name: "EndoRagWidget",
      fileName: () => "widget.js",
    },
    // ASCII only (French text as \u escapes): host pages may not declare UTF-8.
    rolldownOptions: { output: { charset: "ascii" } },
  },
});
