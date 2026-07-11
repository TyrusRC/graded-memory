/// <reference types="vite/client" />

interface ImportMetaEnv {
  // Absolute API base for the hosted build (e.g. https://graded-memory-api.onrender.com/api).
  // Unset in local dev, where the Vite proxy forwards the relative "/api".
  readonly VITE_API_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
