import React from "react";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";

export default function KPICard({ label, value, caption, icon: Icon, tone = "navy", trend }) {
  return (
    <article className="kpi-card">
      <div className="kpi-top">
        <span className={`kpi-icon kpi-${tone}`}>{Icon && <Icon size={19} strokeWidth={2} />}</span>
        {trend && (
          <span className={`kpi-trend ${trend.direction === "down" ? "trend-down" : ""}`}>
            {trend.direction === "down" ? <ArrowDownRight size={14} /> : <ArrowUpRight size={14} />}
            {trend.label}
          </span>
        )}
      </div>
      <div className="kpi-value">{value}</div>
      <div className="kpi-label">{label}</div>
      {caption && <div className="kpi-caption">{caption}</div>}
    </article>
  );
}