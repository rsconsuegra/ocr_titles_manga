import { BrowserRouter, Route, Routes, useLocation } from "react-router-dom";

import Sidebar from "./components/Sidebar";
import { ThemeProvider } from "./components/ThemeProvider";
import TopBar from "./components/TopBar";
import BatchRunDetail from "./pages/BatchRunDetail";
import BatchRuns from "./pages/BatchRuns";
import Catalog from "./pages/Catalog";
import Dashboard from "./pages/Dashboard";
import OcrPlayground from "./pages/OcrPlayground";
import PreprocessPlayground from "./pages/PreprocessPlayground";
import ProfileEditor from "./pages/ProfileEditor";
import Profiles from "./pages/Profiles";
import QuickRun from "./pages/QuickRun";
import RunDetail from "./pages/RunDetail";
import Runs from "./pages/Runs";
import Settings from "./pages/Settings";
import Upload from "./pages/Upload";

function AppShell() {
  const location = useLocation();

  return (
    <div className="flex min-h-screen bg-cream">
      <Sidebar />
      <div className="flex-1 flex flex-col ml-[220px]">
        <TopBar />
        <main className="flex-1 p-6">
          <div className="mx-auto max-w-6xl animate-fade-in" key={location.pathname}>
            <Routes location={location}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/runs" element={<Runs />} />
              <Route path="/runs/:id" element={<RunDetail />} />
              <Route path="/batches" element={<BatchRuns />} />
              <Route path="/batches/:id" element={<BatchRunDetail />} />
              <Route path="/catalog" element={<Catalog />} />
              <Route path="/playground/ocr" element={<OcrPlayground />} />
              <Route path="/playground/preprocess" element={<PreprocessPlayground />} />
              <Route path="/run/quick" element={<QuickRun />} />
              <Route path="/run/pipeline" element={<Upload />} />
              <Route path="/upload" element={<Upload />} />
              <Route path="/profiles" element={<Profiles />} />
              <Route path="/profiles/new" element={<ProfileEditor />} />
              <Route path="/profiles/:id/edit" element={<ProfileEditor />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/preprocess" element={<PreprocessPlayground />} />
            </Routes>
          </div>
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AppShell />
      </ThemeProvider>
    </BrowserRouter>
  );
}
