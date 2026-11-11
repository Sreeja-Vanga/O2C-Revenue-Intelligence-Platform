import React from "react";
import { AlertTriangle, LoaderCircle, RefreshCw, SearchX } from "lucide-react";

export function LoadingState({ label = "Loading data…" }) {
  return <div className="state-panel"><LoaderCircle className="spin" size={23} /><span>{label}</span></div>;
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="state-panel state-error">
      <AlertTriangle size={21} />
      <div><strong>We couldn’t load this data</strong><span>{message}</span></div>
      {onRetry && <button className="button button-secondary button-small" onClick={onRetry}><RefreshCw size={14} />Retry</button>}
    </div>
  );
}

export function EmptyState({ title = "No records found", message = "Try adjusting your filters." }) {
  return <div className="state-panel state-empty"><SearchX size={22} /><div><strong>{title}</strong><span>{message}</span></div></div>;
}
