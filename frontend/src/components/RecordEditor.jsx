import React from "react";
import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { transactionApi } from "../services/api";

const STATUS_OPTIONS = {
  accounts: ["ACTIVE", "INACTIVE", "CREDIT_HOLD"],
  quotes: ["DRAFT", "OPEN", "APPROVED", "REJECTED", "EXPIRED", "CONVERTED"],
  orders: ["DRAFT", "CONFIRMED", "PARTIALLY_SHIPPED", "SHIPPED", "CLOSED", "CANCELLED"],
  shipments: ["PLANNED", "SHIPPED", "DELIVERED", "CANCELLED"],
  invoices: ["DRAFT", "ISSUED", "PARTIALLY_PAID", "PAID", "DISPUTED", "VOID"],
  payments: ["RECEIVED", "PARTIALLY_APPLIED", "APPLIED", "VOID"],
  disputes: ["OPEN", "UNDER_REVIEW", "APPROVED", "REJECTED", "CLOSED"],
  events: [],
};

function initialValues(fields, record) {
  return Object.fromEntries(fields.filter((field) => field.writable).map((field) => {
    let value = record?.[field.name] ?? field.default ?? "";
    if (field.data_type === "date" && value) value = String(value).slice(0, 10);
    if (field.data_type === "datetime" && value) value = String(value).slice(0, 16);
    return [field.name, value];
  }));
}

export default function RecordEditor({ open, resource, record, onClose, onSubmit }) {
  const [schema, setSchema] = useState(null);
  const [values, setValues] = useState({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return undefined;
    let active = true;
    setLoading(true);
    setError("");
    transactionApi.schema(resource).then((result) => {
      if (!active) return;
      setSchema(result);
      setValues(initialValues(result.fields, record));
    }).catch((requestError) => {
      if (active) setError(requestError.message);
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [open, resource, record]);

  if (!open) return null;

  const save = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const payload = {};
      for (const field of schema.fields.filter((item) => item.writable)) {
        const value = values[field.name];
        if (value === "" && field.nullable) {
          payload[field.name] = null;
        } else if (["int", "integer", "bigint", "smallint", "tinyint", "mediumint", "decimal", "float", "double", "real"].includes(field.data_type)) {
          const number = Number(value);
          if (!Number.isFinite(number)) throw new Error(`${field.name} must be a valid number.`);
          payload[field.name] = number;
        } else if (field.data_type === "datetime" && typeof value === "string" && value) {
          payload[field.name] = value.replace("T", " ") + (value.length === 16 ? ":00" : "");
        } else {
          payload[field.name] = value;
        }
      }
      await onSubmit(payload);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  };

  const fields = schema?.fields.filter((field) => field.writable) || [];
  return (
    <div className="editor-scrim" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="record-editor" role="dialog" aria-modal="true" aria-labelledby="record-editor-title">
        <header><div><span className="eyebrow">{record ? "EDIT RECORD" : "NEW RECORD"}</span><h2 id="record-editor-title">{resource.replaceAll("_", " ")}</h2></div><button className="icon-button" onClick={onClose} aria-label="Close form"><X size={18} /></button></header>
        {loading ? <div className="editor-message">Loading fields…</div> : error && !schema ? <div className="inline-error">{error}</div> : (
          <form onSubmit={save}>
            <div className="editor-fields">
              {fields.map((field) => {
                const isStatus = field.name === "status" && STATUS_OPTIONS[resource]?.length;
                const inputType = field.data_type === "date" ? "date"
                  : field.data_type === "datetime" ? "datetime-local"
                    : ["int", "integer", "bigint", "smallint", "tinyint", "mediumint", "decimal", "float", "double", "real"].includes(field.data_type) ? "number" : "text";
                return (
                  <label className="editor-field" key={field.name}>
                    <span>{field.name.replaceAll("_", " ")}{field.required ? " *" : ""}</span>
                    {isStatus ? <select required={field.required} value={values[field.name] ?? ""} onChange={(event) => setValues((current) => ({ ...current, [field.name]: event.target.value }))}>
                      {!field.required && <option value="">—</option>}
                      {STATUS_OPTIONS[resource].map((status) => <option key={status} value={status}>{status.replaceAll("_", " ")}</option>)}
                    </select> : field.name === "note" ? <textarea value={values[field.name] ?? ""} required={field.required} onChange={(event) => setValues((current) => ({ ...current, [field.name]: event.target.value }))} /> : (
                      <input type={inputType} step={["decimal", "float", "double", "real"].includes(field.data_type) ? "any" : undefined} value={values[field.name] ?? ""} required={field.required} onChange={(event) => setValues((current) => ({ ...current, [field.name]: event.target.value }))} />
                    )}
                  </label>
                );
              })}
            </div>
            {error && <div className="inline-error">{error}</div>}
            <footer><button type="button" className="button button-secondary" onClick={onClose} disabled={saving}>Cancel</button><button type="submit" className="button button-primary" disabled={saving}>{saving ? "Saving…" : "Save record"}</button></footer>
          </form>
        )}
      </section>
    </div>
  );
}
