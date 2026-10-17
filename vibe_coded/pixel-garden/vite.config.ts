import { defineConfig } from 'vitest/config';
import { fileURLToPath } from 'node:url';

export default defineConfig({
  root: 'frontend',
  server: { host: '127.0.0.1', fs: { allow: [fileURLToPath(new URL('.', import.meta.url))] }, proxy: { '/api': 'http://127.0.0.1:8000' } },
  build: { outDir: '../dist', emptyOutDir: true },
  test: { include: ['src/**/*.test.ts'], environment: 'node' },
});
