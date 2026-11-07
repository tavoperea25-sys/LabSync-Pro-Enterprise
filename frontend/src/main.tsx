import React from "react";
import ReactDOM from "react-dom/client";
import { z } from "zod";

import { App } from "@/app/App";
import "@/shared/styles/globals.css";

// Mensajes por defecto de zod (los que no llevan `error` explícito, p. ej.
// los .max() sin mensaje) en español — una sola vez, al arrancar la app.
z.config(z.locales.es());

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
