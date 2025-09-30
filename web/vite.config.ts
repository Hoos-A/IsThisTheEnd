import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import fs from "fs";

const certPath = process.env.DEV_SSL_CERT;
const keyPath = process.env.DEV_SSL_KEY;
const https = certPath && keyPath ? { cert: fs.readFileSync(certPath), key: fs.readFileSync(keyPath) } : false;

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    https
  }
});
