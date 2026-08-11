import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
export default defineConfig({
  // teamarcher.in is served from the domain root, not a repository subpath.
  base: '/',
  plugins: [react()],
})
