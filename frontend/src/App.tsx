import { useRef, useState } from "react";
import { BrowserRouter, NavLink, Route, Routes, useLocation } from "react-router-dom";

import { DsoBrandStrip, DsoScrew } from "./components/dso";
import Catalog from "./pages/Catalog";
import Dashboard from "./pages/Dashboard";
import OcrPlayground from "./pages/OcrPlayground";
import PreprocessPlayground from "./pages/PreprocessPlayground";
import ProfileEditor from "./pages/ProfileEditor";
import Profiles from "./pages/Profiles";
import QuickRun from "./pages/QuickRun";
import RunDetail from "./pages/RunDetail";
import Runs from "./pages/Runs";
import BatchRuns from "./pages/BatchRuns";
import BatchRunDetail from "./pages/BatchRunDetail";
import Upload from "./pages/Upload";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  [
    "px-3 py-2 rounded text-sm font-medium transition-all duration-150",
    isActive
      ? "text-teal bg-teal/10 shadow-[inset_0_0_8px_rgba(56,178,172,0.1)]"
      : "text-muted hover:text-bright hover:bg-panel-light/50",
  ].join(" ");

interface NavGroupProps {
  label: string;
  children: React.ReactNode;
  locationPath: string;
}

function NavGroup({ label, children, locationPath }: NavGroupProps) {
  const [open, setOpen] = useState(false);
  const prevPath = useRef(locationPath);
  const closeTimer = useRef<ReturnType<typeof setTimeout>>(null);

  if (prevPath.current !== locationPath) {
    prevPath.current = locationPath;
    if (open) setOpen(false);
  }

  function scheduleClose() {
    closeTimer.current = setTimeout(() => setOpen(false), 200);
  }

  function cancelClose() {
    if (closeTimer.current) clearTimeout(closeTimer.current);
    setOpen(true);
  }

  return (
    <div className="relative" onMouseEnter={cancelClose} onMouseLeave={scheduleClose}>
      <button
        className="px-3 py-2 rounded text-sm font-medium transition-colors text-muted hover:text-bright hover:bg-panel-light/50 cursor-pointer"
        onClick={() => setOpen(!open)}
      >
        {label} <span className="text-muted/60">&#9662;</span>
      </button>
      {open && (
        <div className="absolute left-0 top-full z-10 mt-1 w-44 neo-panel border border-highlight/20 py-1">
          {children}
        </div>
      )}
    </div>
  );
}

function SubLink({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        [
          "block px-4 py-2 text-sm transition-colors",
          isActive
            ? "text-teal bg-teal/10 font-medium"
            : "text-muted hover:text-bright hover:bg-panel-light/50",
        ].join(" ")
      }
    >
      {children}
    </NavLink>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppShell />
    </BrowserRouter>
  );
}

function AppShell() {
  const location = useLocation();

  return (
    <div className="flex min-h-screen flex-col bg-chassis">
      <DsoBrandStrip variant="header">
        <div className="mx-auto flex w-full max-w-7xl items-center gap-1">
          <div className="mr-4 flex items-center gap-2.5">
            <span className="led led-active" />
            <span className="font-display text-lg font-bold tracking-wide text-bright">
              MANGA OCR
            </span>
          </div>
          <NavLink to="/" className={navLinkClass} end>
            Dashboard
          </NavLink>
          <NavGroup label="History" locationPath={location.pathname}>
            <SubLink to="/runs">Runs</SubLink>
            <SubLink to="/batches">Batches</SubLink>
            <SubLink to="/catalog">Catalog</SubLink>
          </NavGroup>
          <NavGroup label="Playground" locationPath={location.pathname}>
            <SubLink to="/playground/preprocess">Preprocessing</SubLink>
            <SubLink to="/playground/ocr">OCR</SubLink>
          </NavGroup>
          <NavGroup label="Run" locationPath={location.pathname}>
            <SubLink to="/run/quick">Quick Run</SubLink>
            <SubLink to="/run/pipeline">Full Pipeline</SubLink>
          </NavGroup>
          <NavGroup label="Config" locationPath={location.pathname}>
            <SubLink to="/profiles">Profiles</SubLink>
          </NavGroup>
          <div className="ml-auto flex items-center gap-2">
            <DsoScrew />
          </div>
        </div>
      </DsoBrandStrip>

      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/runs" element={<Runs />} />
          <Route path="/runs/:id" element={<RunDetail />} />
          <Route path="/batches" element={<BatchRuns />} />
          <Route path="/batches/:id" element={<BatchRunDetail />} />
          <Route path="/profiles" element={<Profiles />} />
          <Route path="/profiles/new" element={<ProfileEditor />} />
          <Route path="/profiles/:id/edit" element={<ProfileEditor />} />
          <Route path="/catalog" element={<Catalog />} />
          <Route path="/playground/preprocess" element={<PreprocessPlayground />} />
          <Route path="/playground/ocr" element={<OcrPlayground />} />
          <Route path="/run/quick" element={<QuickRun />} />
          <Route path="/run/pipeline" element={<Upload />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/preprocess" element={<PreprocessPlayground />} />
        </Routes>
      </main>

      <DsoBrandStrip variant="footer">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between">
          <span className="tech-label">Manga OCR v0.1</span>
          <div className="flex items-center gap-3">
            <span className="led led-active" />
            <span className="tech-label-bright">System Ready</span>
          </div>
        </div>
      </DsoBrandStrip>
    </div>
  );
}
