/// <reference types="vite/client" />

interface Window {
  telemu?: {
    platform: string;
    isElectron: boolean;
  };
}
