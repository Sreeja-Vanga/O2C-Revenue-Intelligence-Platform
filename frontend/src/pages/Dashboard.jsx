import React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertOctagon,
  ArrowUpRight,
  BadgeDollarSign,
  CircleDollarSign,
  Clock3,
  FileWarning,
  RefreshCw,
  Wallet,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Link } from "react-router-dom";
import { analyticsApi, dashboardApi, exceptionApi } from "../services/api";
import ChartCard from "../components/ChartCard";
import DataTable from "../components/DataTable";
import KPICard from "../components/KPICard";
import { ErrorState, LoadingState } from "../components/PageState";
import StatusBadge from "../components/StatusBadge";
import { formatAmount, formatCurrency, formatMonth, formatNumber } from "../utils/format";

const chartTooltip = {
  contentStyle: { border: "1px solid #e8edf4", borderRadius: 10, boxShadow: "0 8px 24px #172b4d14" },
  formatter: (value, name) => [name.toLowerCase().includes("amount") || name.toLowerCase().includes("revenue") || name.toLowerCase().includes("payment") ? formatAmount(value) : formatNumber(value), name],
};

function sumStatuses(rows = [], statuses) {
  return rows.filter((row) => statuses.includes(row.status)).reduce((total, row) => total + Number(row.count || 0), 0);
}

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [overview, revenue, lifecycle, trends, aging, payment, disputes, exceptions] = await Promise.all([
        dashboardApi.overview(),
        dashboardApi.revenue(),
        dashboardApi.lifecycle(),
        analyticsApi.trends(),
        analyticsApi.invoiceAging(),
        analyticsApi.paymentPerformance(),
        analyticsApi.disputeAnalysis(),
        exceptionApi.list({ page: 1, per_page: 6, sort_by: "detected_at", sort_order: "desc" }),
      ]);
      setData({ overview, revenue, lifecycle, trends, aging, payment, disputes, exceptions });
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const lifecycleRows = useMemo(() => {
    if (!data) return [];
    const orders = data.lifecycle.orders_by_status || [];
    const invoices = data.lifecycle.invoices_by_status || [];
    const totalOrders = orders.reduce((sum, item) => sum + Number(item.count), 0);
    const totalInvoices = invoices.reduce((sum, item) => sum + Number(item.count), 0);
    return [
      { stage: "Orders", total: totalOrders, complete: sumStatuses(orders, ["CLOSED", "SHIPPED"]) },
      { stage: "Shipments", total: (data.lifecycle.shipments_by_status || []).reduce((sum, item) => sum + Number(item.count), 0), complete: sumStatuses(data.lifecycle.shipments_by_status, ["DELIVERED"]) },
      { stage: "Invoices", total: totalInvoices, complete: sumStatuses(invoices, ["PAID"]) },
    ];
  }, [data]);

  if (loading) return <LoadingState label="Preparing your revenue overview…" />;
  if (error && !data) return <ErrorState message={error} onRetry={load} />;

  const overview = data?.overview || {};
  const revenue = data?.revenue || {};
  const trends = data?.trends?.items || [];
  const aging = data?.aging?.items || [];
  const payments = data?.payment || {};
  const recent = data?.exceptions?.items || [];
  const openDisputes = sumStatuses(data?.disputes?.by_status, ["OPEN", "UNDER_REVIEW"]);
  const tableColumns = [
    { key: "exception_id", label: "Exception ID" },
    { key: "anomaly_code", label: "Anomaly type", render: (row) => <span className="anomaly-name">{row.anomaly_code?.replaceAll("_", " ")}</span> },
    { key: "severity", label: "Severity", render: (row) => <StatusBadge value={row.severity} /> },
    { key: "status", label: "Status", render: (row) => <StatusBadge value={row.status} /> },
    { key: "detected_at", label: "Detected", render: (row) => row.detected_at ? new Date(row.detected_at).toLocaleDateString() : "—" },
  ];

  return (
    <div className="page-stack">
      <div className="page-heading-row">
        <div><span className="eyebrow">OVERVIEW</span><h2>Revenue at a glance</h2><p>Monitor cash flow, receivables, and operational exceptions across the order-to-cash cycle.</p></div>
        <button className="button button-secondary" onClick={load}><RefreshCw size={16} />Refresh data</button>
      </div>
      {error && <div className="inline-error">{error}</div>}
      <div className="kpi-grid">
        <KPICard label="Total invoiced revenue" value={formatCurrency(revenue.total_invoiced_amount)} caption={`${formatNumber(overview.total_invoices)} invoices issued`} icon={BadgeDollarSign} tone="navy" />
        <KPICard label="Outstanding receivables" value={formatCurrency(revenue.outstanding_amount)} caption="Open invoice balances" icon={Clock3} tone="amber" />
        <KPICard label="Payments collected" value={formatCurrency(revenue.total_collected_amount)} caption={`${formatNumber(payments.payment_count)} recorded payments`} icon={Wallet} tone="green" />
        <KPICard label="Revenue leakage" value={formatCurrency(revenue.revenue_leakage_amount)} caption="Recorded exception variance" icon={CircleDollarSign} tone="red" />
        <KPICard label="Open disputes" value={formatNumber(openDisputes)} caption="Open or under review" icon={AlertOctagon} tone="purple" />
        <KPICard label="Detected exceptions" value={formatNumber(overview.total_exceptions)} caption={`${formatNumber(overview.open_exceptions)} currently open`} icon={FileWarning} tone="blue" />
      </div>

      <div className="dashboard-chart-grid">
        <ChartCard title="Revenue and collections" description="Monthly invoice totals compared with payment receipts, based on transaction dates." className="chart-wide">
          {trends.length ? (
            <div className="chart-area">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trends} margin={{ top: 8, right: 12, left: 3, bottom: 0 }}>
                  <defs>
                    <linearGradient id="invoiceFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#5278dd" stopOpacity={0.19} /><stop offset="95%" stopColor="#5278dd" stopOpacity={0} /></linearGradient>
                    <linearGradient id="paymentFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#2db596" stopOpacity={0.15} /><stop offset="95%" stopColor="#2db596" stopOpacity={0} /></linearGradient>
                  </defs>
                  <CartesianGrid stroke="#edf1f6" vertical={false} />
                  <XAxis dataKey="month" tickFormatter={formatMonth} tickLine={false} axisLine={false} />
                  <YAxis tickFormatter={(value) => `$${Math.round(value / 1000)}k`} tickLine={false} axisLine={false} width={52} />
                  <Tooltip {...chartTooltip} labelFormatter={formatMonth} />
                  <Legend />
                  <Area type="monotone" dataKey="invoiced_amount" name="Invoiced revenue" stroke="#5278dd" strokeWidth={2.5} fill="url(#invoiceFill)" />
                  <Area type="monotone" dataKey="payment_amount" name="Payments collected" stroke="#2db596" strokeWidth={2.5} fill="url(#paymentFill)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : <div className="chart-empty">No monthly revenue activity is available.</div>}
        </ChartCard>

        <ChartCard title="Invoice aging" description="Unpaid invoice balance grouped by how long the invoice is past due.">
          {aging.length ? (
            <div className="chart-area chart-area-short">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={aging} margin={{ top: 8, right: 8, left: 4, bottom: 0 }}>
                  <CartesianGrid stroke="#edf1f6" vertical={false} />
                  <XAxis dataKey="aging_bucket" tickFormatter={(value) => value.replaceAll("_", " ")} tickLine={false} axisLine={false} tick={{ fontSize: 10 }} />
                  <YAxis tickFormatter={(value) => `$${Math.round(value / 1000)}k`} tickLine={false} axisLine={false} width={48} />
                  <Tooltip {...chartTooltip} />
                  <Bar dataKey="outstanding_amount" name="Outstanding balance" fill="#e1a63b" radius={[5, 5, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : <div className="chart-empty">No overdue balances to display.</div>}
        </ChartCard>
      </div>

      <div className="dashboard-bottom-grid">
        <ChartCard title="Order-to-cash lifecycle" description="Current document volumes at each stage. Completed bars show closed or paid volumes.">
          <div className="lifecycle-list">
            {lifecycleRows.map((row) => {
              const percent = row.total ? Math.min((row.complete / row.total) * 100, 100) : 0;
              return <div className="lifecycle-row" key={row.stage}><div className="lifecycle-label"><strong>{row.stage}</strong><span>{formatNumber(row.complete)} completed of {formatNumber(row.total)}</span></div><div className="progress-track"><div className="progress-fill" style={{ width: `${percent}%` }} /></div></div>;
            })}
          </div>
        </ChartCard>
        <ChartCard title="Payment performance" description="Cash received, allocations posted, and reported unapplied amount.">
          <div className="payment-performance">
            <div><span>Received</span><strong>{formatAmount(payments.payment_total)}</strong></div>
            <div><span>Allocated</span><strong>{formatAmount(payments.allocation_total)}</strong></div>
            <div><span>Unapplied (reported)</span><strong>{formatAmount(payments.reported_unapplied_total)}</strong></div>
            <div className="collection-rate"><span>Collection rate</span><strong>{formatNumber(payments.collection_rate_pct, 1)}%</strong></div>
          </div>
        </ChartCard>
      </div>

      <section className="section-block">
        <div className="section-heading"><div><h3>Recent exceptions</h3><p>Latest issues recorded in the exception register.</p></div><Link className="text-link" to="/exceptions">View all exceptions <ArrowUpRight size={15} /></Link></div>
        <DataTable columns={tableColumns} rows={recent} loading={false} emptyTitle="No exceptions recorded" />
      </section>
    </div>
  );
}