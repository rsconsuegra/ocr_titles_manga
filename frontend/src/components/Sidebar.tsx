import { NavLink, useLocation } from "react-router-dom";

const NAV_SECTIONS = [
  {
    label: "WORKFLOW",
    items: [
      { to: "/run/pipeline", text: "Upload Images" },
      { to: "/run/quick", text: "Quick Run" },
    ],
  },
  {
    label: "RESULTS",
    items: [
      { to: "/runs", text: "Pipeline Runs" },
      { to: "/batches", text: "Batch Runs" },
      { to: "/catalog", text: "Catalog" },
    ],
  },
  {
    label: "EXPERIMENT",
    items: [
      { to: "/playground/ocr", text: "OCR Playground" },
      { to: "/playground/preprocess", text: "Preprocess Playground" },
    ],
  },
  {
    label: "CONFIGURE",
    items: [
      { to: "/profiles", text: "Profiles" },
      { to: "/settings", text: "Settings" },
    ],
  },
];

const PREFIX_ROUTES: Record<string, string> = {
  "/runs/": "/runs",
  "/batches/": "/batches",
  "/profiles/": "/profiles",
};

export default function Sidebar() {
  const location = useLocation();

  const isActive = (to: string) => {
    if (location.pathname === to) return true;
    if (PREFIX_ROUTES[to + "/"] && location.pathname.startsWith(to + "/")) return true;
    if (to === "/run/pipeline" && location.pathname === "/upload") return true;
    if (to === "/playground/preprocess" && location.pathname === "/preprocess") return true;
    return false;
  };

  return (
    <aside className="fixed left-0 top-0 bottom-0 w-[220px] bg-sidebar border-r border-sidebar-border flex flex-col z-10">
      <div className="px-5 pt-6 pb-4">
        <h1 className="font-display text-[18px] font-semibold text-ink">Manga OCR</h1>
      </div>

      <nav className="flex-1 overflow-y-auto px-3">
        {NAV_SECTIONS.map((section) => (
          <div key={section.label} className="mb-6">
            <div className="label-text px-3 mb-2">{section.label}</div>
            <ul>
              {section.items.map((item) => (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    className={() => {
                      const active = isActive(item.to);
                      return `block px-3 py-2 rounded-md text-[14px] font-body transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo/20 focus-visible:ring-offset-1 ${
                        active
                          ? "bg-indigo-pale text-indigo font-semibold"
                          : "text-charcoal hover:bg-cream hover:text-ink"
                      }`;
                    }}
                  >
                    {item.text}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      <div className="px-5 py-4">
        <span className="text-[11px] text-sand font-body">v0.1</span>
      </div>
    </aside>
  );
}
