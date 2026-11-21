import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Locally, the page calls /api/... and Vite forwards it to the Python API on port 8000.
// In Kubernetes, the web container (nginx) does the same forwarding, so the browser only ever talks to one address.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", rewrite: (path) => path.replace(/^\/api/, "") },
    },
  },
});
