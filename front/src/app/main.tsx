// Entry of the single-page assistant (index.html), the product the campaign's QR codes open.
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./app.css";

createRoot(document.getElementById("root")!).render(<App />);
