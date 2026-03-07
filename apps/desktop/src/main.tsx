import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import Spotlight from "./pages/Spotlight";
import "./index.css";

const isSpotlight = window.location.search.includes("spotlight=true");

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    {isSpotlight ? <Spotlight /> : <App />}
  </React.StrictMode>
);
