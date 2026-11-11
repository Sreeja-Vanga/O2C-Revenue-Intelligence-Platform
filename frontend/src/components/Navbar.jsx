import React from "react";
import { Menu, Search, Command } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

const pageNames = {
  "/": "Dashboard",
  "/exceptions": "Exception management",
  "/detection": "Detection engine",
  "/analytics": "Analytics",
};

export default function Navbar({ onMenuClick }) {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const pageName = pathname.startsWith("/transactions")
    ? "Transactions"
    : pageNames[pathname] || "Revenue operations";

  return (
    <header className="topbar">
      <div className="topbar-title">
        <button className="mobile-menu icon-button" onClick={onMenuClick} aria-label="Open navigation">
          <Menu size={20} />
        </button>
        <div>
          <div className="breadcrumb">REVENUE OPERATIONS <span>/</span> <strong>{pageName}</strong></div>
          <h1>{pageName}</h1>
        </div>
      </div>
      <div className="topbar-actions">
        <button className="global-search-hint" onClick={() => navigate("/exceptions")} title="Open exception search">
          <Search size={16} />
          <span>Search records</span>
          <kbd><Command size={11} /> K</kbd>
        </button>
        <div className="topbar-divider" />
        <div className="topbar-user">
          <div className="user-avatar">RI</div>
          <div className="user-details"><strong>Revenue Intelligence</strong><span>Finance workspace</span></div>
        </div>
      </div>
    </header>
  );
}