import type { ReactNode } from "react";
import { matchPath, useLocation } from "react-router-dom";
import ThemeToggle from "./ThemeToggle";

const PAGE_TITLES: { pattern: string; title: string }[] = [
  { pattern: "/runs/:id", title: "Run Detail" },
  { pattern: "/batches/:id", title: "Batch Detail" },
  { pattern: "/profiles/:id/edit", title: "Edit Profile" },
  { pattern: "/profiles/new", title: "New Profile" },
  { pattern: "/run/quick", title: "Quick Run" },
  { pattern: "/run/pipeline", title: "Upload Images" },
  { pattern: "/playground/ocr", title: "OCR Playground" },
  { pattern: "/playground/preprocess", title: "Preprocess Playground" },
  { pattern: "/runs", title: "Pipeline Runs" },
  { pattern: "/batches", title: "Batch Runs" },
  { pattern: "/catalog", title: "Catalog" },
  { pattern: "/profiles", title: "Profiles" },
  { pattern: "/settings", title: "Settings" },
  { pattern: "/", title: "Dashboard" },
];

function getPageTitle(pathname: string): string {
  for (const { pattern, title } of PAGE_TITLES) {
    if (matchPath(pattern, pathname)) {
      return title;
    }
  }
  return "Manga OCR";
}

interface TopBarProps {
  actions?: ReactNode;
}

export default function TopBar({ actions }: TopBarProps) {
  const location = useLocation();
  const pageTitle = getPageTitle(location.pathname);

  return (
    <header className="h-14 bg-snow border-b border-linen flex items-center justify-between px-6 sticky top-0 z-10">
      <h2 className="font-display text-[20px] font-semibold text-ink">{pageTitle}</h2>
      <div className="flex items-center gap-4">
        {actions}
        <ThemeToggle />
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-success" />
          <span className="text-[13px] text-charcoal font-body">Connected</span>
        </div>
      </div>
    </header>
  );
}
