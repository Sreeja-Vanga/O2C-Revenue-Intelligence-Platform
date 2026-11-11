import React from "react";
import {
  Activity,
  BarChart3,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  Database,
  FileStack,
  LayoutDashboard,
  ScanSearch,
  WalletCards,
} from "lucide-react";
import { NavLink } from "react-router-dom";

const primaryLinks = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/transactions/quotes", label: "Transactions", icon: FileStack },
  { to: "/exceptions", label: "Exceptions", icon: CircleAlert },
  { to: "/detection", label: "Detection engine", icon: ScanSearch },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/synthetic-data", label: "Synthetic data", icon: Database },
];

export default function Sidebar({ open, onClose, collapsed, onToggleCollapsed }) {
  return (
    <>
      <button
        className={`sidebar-scrim ${open ? "is-visible" : ""}`}
        aria-label="Close navigation"
        onClick={onClose}
      />
      <aside className={`sidebar ${open ? "is-open" : ""} ${collapsed ? "is-collapsed" : ""}`}>
        <div className="sidebar-brand">
          <div className="brand-mark"><Activity size={21} strokeWidth={2.2} /></div>
          <div className="brand-copy">
            <strong>O2C Intelligence</strong>
            <span>REVENUE OPERATIONS</span>
          </div>
          <button className="sidebar-collapse" onClick={onToggleCollapsed} aria-label="Collapse sidebar">
            {collapsed ? <ChevronRight size={17} /> : <ChevronLeft size={17} />}
          </button>
        </div>
        <div className="sidebar-section-label">WORKSPACE</div>
        <nav className="side-nav" aria-label="Main navigation">
          {primaryLinks.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={onClose}
              title={collapsed ? label : undefined}
              className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
            >
              <Icon size={19} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-bottom-icon"><WalletCards size={18} /></div>
          <div className="sidebar-bottom-copy">
            <strong>Order to cash</strong>
            <span>Revenue visibility, end to end</span>
          </div>
        </div>
      </aside>
    </>
  );
}