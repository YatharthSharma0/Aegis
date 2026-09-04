import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { initTheme } from "./app/theme";
import App from "./App.tsx";
import "./index.css";

initTheme();

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element #root not found");
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
