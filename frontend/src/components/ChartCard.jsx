import React from "react";
import { Info } from "lucide-react";

export default function ChartCard({ title, description, children, className = "" }) {
  return (
    <section className={`chart-card ${className}`}>
      <div className="chart-card-heading">
        <div><h3>{title}</h3><p>{description}</p></div>
        <span className="info-icon" title={description} aria-label={description}><Info size={16} /></span>
      </div>
      {children}
    </section>
  );
}
