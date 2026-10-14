// {{header}}
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_AWARE_SERVER_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
