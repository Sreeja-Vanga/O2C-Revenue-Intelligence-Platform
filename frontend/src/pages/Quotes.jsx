import React from "react";
import { useCallback, useEffect, useState } from "react";
import { CalendarDays, Filter, RotateCcw } from "lucide-react";
import DataTable from "../components/DataTable";
import DetailDrawer from "../components/DetailDrawer";
import { EmptyState, ErrorState, LoadingState } from "../components/PageState";
import StatusBadge from "../components/StatusBadge";
import { transactionApi, downloadCsv } from "../services/api";
import { useToast } from "../components/ToastProvider";
import { formatAmount } from "../utils/format";

export const TRANSACTION_RESOURCES = {
  quotes: {
    label: "Quotes",
    path: "quotes",
    id: "quote_id",
    dateField: "quote_date",
    columns: [
      { key: "quote_id", label: "Quote ID" },
      { key: "account_id", label: "Account" },
      { key: "quote_date", label: "Quote date" },
      { key: "valid_until", label: "Valid until" },
      { key: "total_amount", label: "Quote value", numeric: true, render: (row) => formatAmount(row.total_amount, row.currency_code) },
      { key: "status", label: "Status", render: (row) => <StatusBadge value={row.status} /> },
    ],
  },
  orders: {
    label: "Sales Orders",
    path: "orders",
    id: "sales_order_id",
    dateField: "order_date",
    columns: [
      { key: "sales_order_id", label: "Sales order" },
      { key: "account_id", label: "Account" },
      { key: "quote_id", label: "Source quote" },
      { key: "order_date", label: "Order date" },
      { key: "total_amount", label: "Order value", numeric: true, render: (row) => formatAmount(row.total_amount, row.currency_code) },
      { key: "status", label: "Status", render: (row) => <StatusBadge value={row.status} /> },
    ],
  },
  shipments: {
    label: "Shipments",
    path: "shipments",
    id: "shipment_id",
    dateField: "ship_date",
    columns: [
      { key: "shipment_id", label: "Shipment ID" },
      { key: "sales_order_id", label: "Sales order" },
      { key: "ship_date", label: "Ship date" },
      { key: "carrier", label: "Carrier" },
      { key: "tracking_number", label: "Tracking" },
      { key: "status", label: "Status", render: (row) => <StatusBadge value={row.status} /> },
    ],
  },
  invoices: {
    label: "Invoices",
    path: "invoices",
    id: "invoice_id",
    dateField: "invoice_date",
    columns: [
      { key: "invoice_id", label: "Invoice ID" },
      { key: "sales_order_id", label: "Sales order" },
      { key: "account_id", label: "Account" },
      { key: "invoice_date", label: "Invoice date" },
      { key: "open_amount", label: "Open balance", numeric: true, render: (row) => formatAmount(row.open_amount, row.currency_code) },
      { key: "status", label: "Status", render: (row) => <StatusBadge value={row.status} /> },
    ],
  },
  payments: {
    label: "Payments",
    path: "payments",
    id: "payment_id",
    dateField: "payment_date",
    columns: [
      { key: "payment_id", label: "Payment ID" },
      { key: "account_id", label: "Account" },
      { key: "payment_date", label: "Received" },
      { key: "method", label: "Method" },
      { key: "amount", label: "Payment amount", numeric: true, render: (row) => formatAmount(row.amount, row.currency_code) },
      { key: "status", label: "Status", render: (row) => <StatusBadge value={row.status} /> },
    ],
  },
  disputes: {
    label: "Disputes",
    path: "disputes",
    id: "dispute_id",
    dateField: "opened_date",
    columns: [
      { key: "dispute_id", label: "Dispute ID" },
      { key: "invoice_id", label: "Invoice" },
      { key: "account_id", label: "Account" },
      { key: "reason_code", label: "Reason" },
      { key: "disputed_amount", label: "Claim amount", numeric: true, render: (row) => formatAmount(row.disputed_amount) },
      { key: "status", label: "Status", render: (row) => <StatusBadge value={row.status} /> },
    ],
  },
  events: {
    label: "Status Events",
    path: "events",
    id: "status_event_id",
    dateField: "event_at",
    columns: [
      { key: "status_event_id", label: "Event" },
      { key: "entity_type", label: "Entity" },
      { key: "entity_id", label: "Entity ID" },
      { key: "from_status", label: "From", render: (row) => row.from_status ? <StatusBadge value={row.from_status} /> : "Initial" },
      { key: "to_status", label: "To", render: (row) => <StatusBadge value={row.to_status} /> },
      { key: "event_at", label: "Event time" },
    ],
  },
};

export function useTransactionResource(resource) {
  const [result, setResult] = useState({ items: [], pagination: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filters, setFilters] = useState({ search: "", status: "", date_from: "", date_to: "" });
  const [page, setPage] = useState(1);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await transactionApi.list(resource, {
        page,
        per_page: 15,
        sort_by: TRANSACTION_RESOURCES[resource].dateField,
        sort_order: "desc",
        ...filters,
      });
      setResult(response);
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }, [resource, page, filters]);

  useEffect(() => { load(); }, [load]);
  return { result, loading, error, filters, setFilters, page, setPage, load };
}

export default function Quotes() {
  const { result, loading, error, filters, setFilters, page, setPage, load } = useTransactionResource("quotes");
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const notify = useToast();
  const columns = TRANSACTION_RESOURCES.quotes.columns;

  const updateFilter = (key, value) => {
    setPage(1);
    setFilters((current) => ({ ...current, [key]: value }));
  };
  const viewRecord = async (row) => {
    setDetail({ open: true, data: null, title: row.quote_id });
    setDetailLoading(true);
    setDetailError("");
    try {
      const record = await transactionApi.get("quotes", row.quote_id);
      setDetail((current) => ({ ...current, data: record }));
    } catch (requestError) {
      setDetailError(requestError.message);
    } finally {
      setDetailLoading(false);
    }
  };
  const exportRows = () => {
    try { downloadCsv("quotes.csv", result.items, columns.map((column) => ({ label: column.label, value: (row) => column.render ? row[column.key] : row[column.key] }))); }
    catch (exportError) { notify(exportError.message, "error"); }
  };

  if (error && !result.items.length) return <ErrorState message={error} onRetry={load} />;

  return (
    <div className="page-stack">
      <div className="page-heading-row"><div><span className="eyebrow">TRANSACTIONS</span><h2>{TRANSACTION_RESOURCES.quotes.label}</h2><p>Search commercial quotes and inspect related line items.</p></div><div className="records-count"><strong>{result.pagination?.total?.toLocaleString() ?? "—"}</strong><span>quotes</span></div></div>
      <div className="filter-bar">
        <label className="search-field filter-search"><Filter size={16} /><input value={filters.search} onChange={(event) => updateFilter("search", event.target.value)} placeholder="Search quote or account ID" /></label>
        <label className="date-filter"><CalendarDays size={15} /><span>From</span><input aria-label="Date from" type="date" value={filters.date_from} onChange={(event) => updateFilter("date_from", event.target.value)} /></label>
        <label className="date-filter"><span>To</span><input aria-label="Date to" type="date" value={filters.date_to} onChange={(event) => updateFilter("date_to", event.target.value)} /></label>
        <button className="button button-quiet button-small" onClick={() => { setFilters({ search: "", status: "", date_from: "", date_to: "" }); setPage(1); }}><RotateCcw size={14} />Clear</button>
      </div>
      {error && <div className="inline-error">{error}</div>}
      {loading && !result.items.length ? <LoadingState label="Loading quotes…" /> : (
        <DataTable columns={columns} rows={result.items} loading={loading} pagination={result.pagination} onPageChange={setPage} onView={viewRecord} onExport={exportRows} />
      )}
      <DetailDrawer open={detail?.open} title={detail?.title || "Quote"} data={detail?.data} loading={detailLoading} error={detailError} onClose={() => setDetail(null)} />
    </div>
  );
}