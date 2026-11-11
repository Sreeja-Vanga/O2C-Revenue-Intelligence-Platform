import React from "react";
import { useCallback, useEffect, useState } from "react";
import { Download, RefreshCw } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import ChartCard from "../components/ChartCard";
import DataTable from "../components/DataTable";
import KPICard from "../components/KPICard";
import { ErrorState, LoadingState } from "../components/PageState";
import { useToast } from "../components/ToastProvider";
import { analyticsApi, downloadCsv, downloadFinancialReport } from "../services/api";
import { formatAmount, formatMonth, formatNumber } from "../utils/format";

const tooltipStyle = {
  contentStyle: { border: "1px solid #e8edf4", borderRadius: 10, boxShadow: "0 8px 24px #172b4d14" },
};

function ChartArea({ children, height = "chart-area" }) {
  return <div className={height}><ResponsiveContainer width="100%" height="100%">{children}</ResponsiveContainer></div>;
}

export default function Analytics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const notify = useToast();

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [
        leakage, orders, invoices, payments, trends, aging,
        receivables, disputes, lifecycle, reconciliation, reconciliationDetails,
      ] = await Promise.all([
        analyticsApi.revenueLeakage(),
        analyticsApi.orderPerformance(),
        analyticsApi.invoicePerformance(),
        analyticsApi.paymentPerformance(),
        analyticsApi.trends(),
        analyticsApi.invoiceAging(),
        analyticsApi.outstandingReceivables(),
        analyticsApi.disputeAnalysis(),
        analyticsApi.lifecyclePerformance(),
        analyticsApi.reconciliation(),
        analyticsApi.reconciliationDetails(),
      ]);
      setData({ leakage, orders, invoices, payments, trends, aging, receivables, disputes, lifecycle, reconciliation, reconciliationDetails });
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const exportReport = () => {
    if (!data) return;
    try {
      const rows = [
        ...(data.leakage.items || []).map((row) => ({ section: "Revenue leakage", ...row })),
        ...(data.orders.items || []).map((row) => ({ section: "Order performance", ...row })),
        ...(data.aging.items || []).map((row) => ({ section: "Invoice aging", ...row })),
      ];
      const keys = [...new Set(rows.flatMap((row) => Object.keys(row)))];
      downloadCsv("o2c-analytics.csv", rows, keys.map((key) => ({ label: key, value: (row) => row[key] })));
    } catch (exportError) {
      notify(exportError.message, "error");
    }
  };

  const exportExcel = async () => {
    try {
      await downloadFinancialReport();
      notify("Financial Excel report downloaded.", "success");
    } catch (exportError) {
      notify(exportError.message, "error");
    }
  };

  if (loading) return <LoadingState label="Loading revenue analytics…" />;
  if (error && !data) return <ErrorState message={error} onRetry={load} />;

  const trendRows = data?.trends?.items || [];
  const leakageRows = data?.leakage?.items || [];
  const orderRows = data?.orders?.items || [];
  const agingRows = data?.aging?.items || [];
  const invoiceStatusRows = Object.values(data?.invoices?.by_status || {});
  const disputeRows = data?.disputes?.by_status || [];
  const reconciliationRows = data?.reconciliation?.by_anomaly_type || [];
  const reconciliationDetails = data?.reconciliationDetails?.items || [];
  const receivablesRows = (data?.receivables?.items || []).slice(0, 10);
  const leakageColumns = [
    { key: "anomaly_code", label: "Anomaly category", render: (row) => row.anomaly_code.replaceAll("_", " ") },
    { key: "exception_count", label: "Findings", numeric: true },
    { key: "estimated_leakage", label: "Estimated exposure", numeric: true, render: (row) => formatAmount(row.estimated_leakage) },
  ];
  const receivablesColumns = [
    { key: "account_id", label: "Account ID" },
    { key: "account_name", label: "Account" },
    { key: "invoice_count", label: "Open invoices", numeric: true },
    { key: "outstanding_amount", label: "Receivable", numeric: true, render: (row) => formatAmount(row.outstanding_amount) },
  ];

  return (
    <div className="page-stack">
      <div className="page-heading-row"><div><span className="eyebrow">PERFORMANCE & INSIGHTS</span><h2>Revenue analytics</h2><p>Understand leakage, collections, aging, and throughput using live operational data.</p></div><div className="heading-actions"><button className="button button-secondary" onClick={load}><RefreshCw size={15} />Refresh</button><button className="button button-secondary" onClick={exportReport} disabled={!data}><Download size={15} />Export CSV</button><button className="button button-primary" onClick={exportExcel}><Download size={15} />Excel report</button></div></div>
      {error && <div className="inline-error">{error}</div>}
      <div className="kpi-grid analytics-kpis">
        <KPICard label="Recorded leakage" value={formatAmount(data?.leakage?.total_estimated_leakage)} caption="Positive exception variance" />
        <KPICard label="Open receivables" value={formatAmount(data?.receivables?.total_outstanding_amount)} caption="Positive invoice balances" />
        <KPICard label="Payment collection rate" value={`${formatNumber(data?.payments?.collection_rate_pct, 1)}%`} caption={`${formatAmount(data?.payments?.payment_total)} received`} />
        <KPICard label="Independent findings" value={formatNumber(data?.reconciliation?.total_findings)} caption={`${formatAmount(data?.reconciliation?.total_estimated_exposure)} estimated exposure`} />
      </div>
      <div className="dashboard-chart-grid">
        <ChartCard title="Monthly revenue and cash" description="Invoice totals and non-void payment amounts by transaction month." className="chart-wide">
          {trendRows.length ? <ChartArea><LineChart data={trendRows} margin={{ top: 8, right: 12, left: 3, bottom: 0 }}><CartesianGrid stroke="#edf1f6" vertical={false} /><XAxis dataKey="month" tickFormatter={formatMonth} tickLine={false} axisLine={false} /><YAxis tickFormatter={(value) => `$${Math.round(value / 1000)}k`} tickLine={false} axisLine={false} width={52} /><Tooltip {...tooltipStyle} labelFormatter={formatMonth} formatter={(value) => formatAmount(value)} /><Legend /><Line type="monotone" dataKey="invoiced_amount" name="Invoiced revenue" stroke="#5278dd" strokeWidth={2.5} dot={false} /><Line type="monotone" dataKey="payment_amount" name="Payments collected" stroke="#2db596" strokeWidth={2.5} dot={false} /></LineChart></ChartArea> : <div className="chart-empty">No monthly revenue data is available.</div>}
        </ChartCard>
        <ChartCard title="Invoice aging" description="Unpaid invoice balances by time past the due date.">
          {agingRows.length ? <ChartArea height="chart-area chart-area-short"><BarChart data={agingRows} margin={{ top: 8, right: 8, left: 4, bottom: 0 }}><CartesianGrid stroke="#edf1f6" vertical={false} /><XAxis dataKey="aging_bucket" tickFormatter={(value) => value.replaceAll("_", " ")} tick={{ fontSize: 10 }} tickLine={false} axisLine={false} /><YAxis tickFormatter={(value) => `$${Math.round(value / 1000)}k`} tickLine={false} axisLine={false} width={48} /><Tooltip {...tooltipStyle} formatter={(value) => formatAmount(value)} /><Bar dataKey="outstanding_amount" name="Outstanding" fill="#e1a63b" radius={[5, 5, 0, 0]} /></BarChart></ChartArea> : <div className="chart-empty">No open invoice balance to age.</div>}
        </ChartCard>
      </div>
      <div className="dashboard-chart-grid">
        <ChartCard title="Leakage by exception category" description="Recorded exception variance, grouped by anomaly type.">
          {leakageRows.length ? <ChartArea height="chart-area chart-area-medium"><BarChart data={leakageRows} layout="vertical" margin={{ top: 4, right: 18, left: 16, bottom: 0 }}><CartesianGrid stroke="#edf1f6" horizontal={false} /><XAxis type="number" tickFormatter={(value) => `$${Math.round(value / 1000)}k`} tickLine={false} axisLine={false} /><YAxis type="category" dataKey="anomaly_code" width={138} tickFormatter={(value) => value.replaceAll("_", " ")} tick={{ fontSize: 10 }} tickLine={false} axisLine={false} /><Tooltip {...tooltipStyle} formatter={(value) => formatAmount(value)} /><Bar dataKey="estimated_leakage" name="Recorded variance" fill="#d95757" radius={[0, 5, 5, 0]} /></BarChart></ChartArea> : <div className="chart-empty">No leakage records found.</div>}
        </ChartCard>
        <ChartCard title="Order lifecycle volume" description="Current sales order counts in each recorded status.">
          {orderRows.length ? <ChartArea height="chart-area chart-area-medium"><BarChart data={orderRows} margin={{ top: 8, right: 8, left: 4, bottom: 0 }}><CartesianGrid stroke="#edf1f6" vertical={false} /><XAxis dataKey="status" tickFormatter={(value) => value.replaceAll("_", " ")} tick={{ fontSize: 9 }} interval={0} angle={-15} textAnchor="end" height={48} tickLine={false} axisLine={false} /><YAxis tickLine={false} axisLine={false} /><Tooltip {...tooltipStyle} /><Bar dataKey="order_count" name="Sales orders" fill="#5278dd" radius={[5, 5, 0, 0]} /></BarChart></ChartArea> : <div className="chart-empty">No order data is available.</div>}
        </ChartCard>
      </div>
      <div className="dashboard-chart-grid">
        <ChartCard title="Dispute status" description="Claim values and approved credits by dispute status.">
          {disputeRows.length ? <ChartArea height="chart-area chart-area-medium"><BarChart data={disputeRows} margin={{ top: 8, right: 8, left: 4, bottom: 0 }}><CartesianGrid stroke="#edf1f6" vertical={false} /><XAxis dataKey="status" tickFormatter={(value) => value.replaceAll("_", " ")} tick={{ fontSize: 9 }} interval={0} angle={-15} textAnchor="end" height={48} tickLine={false} axisLine={false} /><YAxis tickFormatter={(value) => `$${Math.round(value / 1000)}k`} tickLine={false} axisLine={false} width={48} /><Tooltip {...tooltipStyle} formatter={(value) => formatAmount(value)} /><Legend /><Bar dataKey="disputed_amount" name="Disputed" fill="#8796ad" radius={[4, 4, 0, 0]} /><Bar dataKey="approved_credit_amount" name="Approved credit" fill="#2db596" radius={[4, 4, 0, 0]} /></BarChart></ChartArea> : <div className="chart-empty">No disputes found.</div>}
        </ChartCard>
        <ChartCard title="Order-to-cash health" description="Conversion, fulfillment, and timing averages calculated from linked source documents.">
          <div className="analytics-metric-list">
            <div><span>Quote conversion</span><strong>{formatNumber(data?.lifecycle?.quotes?.quote_conversion_rate_pct, 1)}%</strong><small>{formatNumber(data?.lifecycle?.quotes?.converted_quotes)} of {formatNumber(data?.lifecycle?.quotes?.quote_count)} quotes</small></div>
            <div><span>Orders with shipments</span><strong>{formatNumber(data?.lifecycle?.fulfillment?.orders_with_shipments)}</strong><small>of {formatNumber(data?.lifecycle?.fulfillment?.order_count)} orders</small></div>
            <div><span>Avg. order to invoice</span><strong>{data?.lifecycle?.timing?.avg_order_to_invoice_days == null ? "—" : `${formatNumber(data.lifecycle.timing.avg_order_to_invoice_days, 1)} days`}</strong><small>First invoice date less order date</small></div>
            <div><span>Avg. invoice to payment</span><strong>{data?.lifecycle?.timing?.avg_invoice_to_payment_days == null ? "—" : `${formatNumber(data.lifecycle.timing.avg_invoice_to_payment_days, 1)} days`}</strong><small>First allocated payment date less invoice date</small></div>
          </div>
        </ChartCard>
      </div>
      <section className="section-block"><div className="section-heading"><div><h3>Revenue leakage detail</h3><p>Exception-ledger estimates by anomaly category.</p></div></div><DataTable columns={leakageColumns} rows={leakageRows} /></section>
      <section className="section-block"><div className="section-heading"><div><h3>Largest open receivables</h3><p>Top ten accounts by current positive invoice balance.</p></div></div><DataTable columns={receivablesColumns} rows={receivablesRows} /></section>
      <section className="section-block"><div className="section-heading"><div><h3>Invoice status performance</h3><p>Counts, gross invoice values, and balances grouped by current invoice status.</p></div></div><DataTable columns={[{ key: "status", label: "Status" }, { key: "invoice_count", label: "Invoices", numeric: true }, { key: "invoice_amount", label: "Invoice total", numeric: true, render: (row) => formatAmount(row.invoice_amount) }, { key: "outstanding_amount", label: "Outstanding", numeric: true, render: (row) => formatAmount(row.outstanding_amount) }]} rows={invoiceStatusRows} /></section>
      <section className="section-block"><div className="section-heading"><div><h3>Independent reconciliation</h3><p>Rule output from source tables; it is separate from the exception register.</p></div></div><DataTable columns={[{ key: "anomaly_code", label: "Rule" }, { key: "finding_count", label: "Findings", numeric: true }, { key: "estimated_exposure", label: "Estimated exposure", numeric: true, render: (row) => formatAmount(row.estimated_exposure) }]} rows={reconciliationRows} /></section>
      <section className="section-block"><div className="section-heading"><div><h3>Source reconciliation findings</h3><p>Invoice, shipment, quote, payment, dispute, and lifecycle variances calculated from the transaction tables.</p></div></div><DataTable columns={[{ key: "anomaly_code", label: "Check" }, { key: "entity_type", label: "Entity" }, { key: "entity_id", label: "Record" }, { key: "expected_value", label: "Expected", render: (row) => row.expected_value == null ? "—" : String(row.expected_value) }, { key: "actual_value", label: "Actual", render: (row) => row.actual_value == null ? "—" : String(row.actual_value) }, { key: "estimated_leakage", label: "Exposure", numeric: true, render: (row) => formatAmount(row.estimated_leakage) }, { key: "explanation", label: "Finding" }]} rows={reconciliationDetails} /></section>
      <section className="section-block"><div className="section-heading"><div><h3>Payment collection details</h3><p>Summary of recorded receipts and posted allocation totals.</p></div></div><div className="metric-summary-card"><div><span>Payments received</span><strong>{formatAmount(data?.payments?.payment_total)}</strong></div><div><span>Allocated to invoices</span><strong>{formatAmount(data?.payments?.allocation_total)}</strong></div><div><span>Reported unapplied cash</span><strong>{formatAmount(data?.payments?.reported_unapplied_total)}</strong></div><div><span>Calculated cash remainder</span><strong>{formatAmount(data?.payments?.calculated_unapplied_total)}</strong></div></div></section>
    </div>
  );
}
