// {{header}}
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { Probe } from '../features/probe/Probe';
import { probeLabel } from '../core/probe';

const root = document.getElementById('root');
if (root) {
  createRoot(root).render(
    <StrictMode>
      <Probe label={probeLabel(import.meta.env.VITE_AWARE_SERVER_URL ?? 'http://localhost:8080')} />
    </StrictMode>,
  );
}
