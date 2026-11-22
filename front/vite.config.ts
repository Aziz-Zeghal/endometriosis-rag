import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The demo host page (index.html). It loads the widget with a classic script tag, like a
// third-party site. In dev, /widget.js is a tiny loader that imports the widget source, so
// edits reload; `vite build -c vite.widget.config.ts` writes the real dist/widget.js.
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    {
      name: "widget-dev-loader",
      apply: "serve",
      configureServer(server) {
        server.middlewares.use("/widget.js", (_req, res) => {
          res.setHeader("content-type", "text/javascript");
          res.end('import("/src/widget/main.tsx");');
        });
      },
    },
  ],
});
