import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
// Relative base so the built console can be opened from any static host
// (or file://-ish preview) without path surprises during a demo.
export default defineConfig({
    base: "./",
    plugins: [react()],
    server: { port: 5173, host: true },
});
