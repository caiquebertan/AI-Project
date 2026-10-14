// {{header}}
import { fileURLToPath } from 'node:url';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

// Tests read spec files (schema examples, constants) from the repository root.
const repoRoot = process.env.AWARE_REPO_ROOT ?? fileURLToPath(new URL('../..', import.meta.url));

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
  test: {
    include: ['src/**/*.test.{ts,tsx}'],
    environment: 'node',
    globals: false,
    env: { AWARE_REPO_ROOT: repoRoot },
  },
});
