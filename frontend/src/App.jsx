import React from "react";
import { useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Navbar from "./components/Navbar";
import Sidebar from "./components/Sidebar";
import { ToastProvider } from "./components/ToastProvider";
import Analytics from "./pages/Analytics";
import Dashboard from "./pages/Dashboard";
import Detection from "./pages/Detection";
import Exceptions from "./pages/Exceptions";
import SyntheticData from "./pages/SyntheticData";
import Transactions from "./pages/Transactions";

function ApplicationShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div className={`app-shell ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}>
      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        collapsed={sidebarCollapsed}
        onToggleCollapsed={() => setSidebarCollapsed((current) => !current)}
      />
      <div className="main-column">
        <Navbar onMenuClick={() => setSidebarOpen(true)} />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/transactions/:resource?" element={<Transactions />} />
            <Route path="/exceptions" element={<Exceptions />} />
            <Route path="/detection" element={<Detection />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/synthetic-data" element={<SyntheticData />} />
            <Route path="/accounts" element={<Navigate to="/transactions/accounts" replace />} />
            <Route path="/quotes" element={<Navigate to="/transactions/quotes" replace />} />
            <Route path="/orders" element={<Navigate to="/transactions/orders" replace />} />
            <Route path="/shipments" element={<Navigate to="/transactions/shipments" replace />} />
            <Route path="/invoices" element={<Navigate to="/transactions/invoices" replace />} />
            <Route path="/payments" element={<Navigate to="/transactions/payments" replace />} />
            <Route path="/disputes" element={<Navigate to="/transactions/disputes" replace />} />
            <Route path="/events" element={<Navigate to="/transactions/events" replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          <footer className="app-footer"><span>O2C Revenue Intelligence</span><span>Live operational data · MySQL-backed</span></footer>
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return <ToastProvider><ApplicationShell /></ToastProvider>;
}