import React from "react";

const STATUS_TONES = {
  OPEN: "amber",
  ACKNOWLEDGED: "blue",
  RESOLVED: "green",
  FALSE_POSITIVE: "slate",
  ACTIVE: "green",
  APPROVED: "green",
  CONVERTED: "green",
  CLOSED: "slate",
  DELIVERED: "green",
  PAID: "green",
  APPLIED: "green",
  PARTIALLY_PAID: "blue",
  PARTIALLY_SHIPPED: "blue",
  UNDER_REVIEW: "purple",
  ISSUED: "blue",
  SHIPPED: "cyan",
  CONFIRMED: "blue",
  REJECTED: "red",
  CANCELLED: "red",
  VOID: "slate",
  HIGH: "red",
  MEDIUM: "amber",
  LOW: "blue",
};

export default function StatusBadge({ value }) {
  if (!value) return <span className="text-muted">—</span>;
  const normalized = String(value).toUpperCase();
  const tone = STATUS_TONES[normalized] || "slate";
  return <span className={`status-badge tone-${tone}`}><span className="status-dot" />{normalized.replaceAll("_", " ")}</span>;
}