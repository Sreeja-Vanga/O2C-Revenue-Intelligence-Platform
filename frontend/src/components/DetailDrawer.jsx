import React from "react";
import { useEffect } from "react";
import { LoaderCircle, X } from "lucide-react";
import { EmptyState, ErrorState } from "./PageState";

function displayValue(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value);
}

export default function DetailDrawer({ title, open, onClose, data, loading, error }) {
  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (event) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="drawer-layer" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <aside className="detail-drawer" role="dialog" aria-modal="true" aria-label={title}>
        <div className="drawer-header">
          <div><span className="eyebrow">RECORD DETAILS</span><h2>{title}</h2></div>
          <button className="icon-button" onClick={onClose} aria-label="Close details"><X size={19} /></button>
        </div>
        <div className="drawer-content">
          {loading && <div className="state-panel"><LoaderCircle className="spin" size={22} /><span>Loading record…</span></div>}
          {error && <ErrorState message={error} />}
          {!loading && !error && !data && <EmptyState title="Record unavailable" />}
          {!loading && data && Object.entries(data).map(([key, value]) => (
            <div className="detail-field" key={key}>
              <span>{key.replaceAll("_", " ")}</span>
              {Array.isArray(value) ? (
                <div className="detail-related">{value.length} related record{value.length === 1 ? "" : "s"}<pre>{displayValue(value)}</pre></div>
              ) : (
                <pre>{displayValue(value)}</pre>
              )}
            </div>
          ))}
        </div>
      </aside>
    </div>
  );
}
