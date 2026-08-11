import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    // Use /teamarcher/ for the GitHub Pages project URL; set / for teamarcher.in later.
    base: env.VITE_BASE_PATH || '/',
    plugins: [react()],
  }
})
