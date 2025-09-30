import fs from "node:fs";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const certPath = process.env.DEV_SSL_CERT ?? "";
const keyPath = process.env.DEV_SSL_KEY ?? "";

const httpsOptions = certPath && keyPath && fs.existsSync(certPath) && fs.existsSync(keyPath)
  ? {
      cert: fs.readFileSync(certPath),
      key: fs.readFileSync(keyPath)
    }
  : undefined;

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    https: httpsOptions
  },
  preview: {
    https: httpsOptions
  }
});
