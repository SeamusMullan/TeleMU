import "./index.css";
import "./widgets";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { initTauriBridge } from "./api/tauri-bridge";

// Initialise the Tauri bridge (no-op outside of Tauri shell)
initTauriBridge();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
