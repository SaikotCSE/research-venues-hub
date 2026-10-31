import "./styles/index.css";

import * as React from "react";
import { createRoot } from "react-dom/client";

import { App, routerReady } from "./app";
import { seedInitialData } from "./lib/query";

seedInitialData();

// Keep the server-rendered shell on screen until the page chunk (preloaded by Django) is ready, then render
// once — inside a transition so React time-slices the work instead of blocking the main thread.
const root = createRoot(document.getElementById("root")!);
routerReady().then(() => {
  React.startTransition(() => {
    root.render(
      <React.StrictMode>
        <App />
      </React.StrictMode>,
    );
  });
});
