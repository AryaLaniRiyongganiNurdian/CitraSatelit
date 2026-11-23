import "@fontsource/space-grotesk/latin-400.css";
import "@fontsource/ibm-plex-mono/latin-400.css";
import "./index.css";
import "./app.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "@/app";
import { AppProviders } from "@/contexts";

const container = document.getElementById("root");
if (!container) throw new Error("Elemen root tidak ditemukan.");

createRoot(container).render(
  <StrictMode>
    <AppProviders>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </AppProviders>
  </StrictMode>,
);
