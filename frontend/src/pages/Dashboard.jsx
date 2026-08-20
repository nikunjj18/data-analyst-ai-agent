import { useEffect, useState } from "react";
import {
  LineChart, Line, PieChart, Pie, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, Legend, ScatterChart, Scatter,
} from "recharts";
import { Sparkles, AlertTriangle, TrendingUp, TrendingDown, Minus, Table2, Download } from "lucide-react";
import { exportDashboardUrl } from "../api";
import { useDataset } from "../DatasetContext";
import { api, getTableDashboard } from "../api";

const COLORS = ["#00D4B8", "#F5A623", "#FF6B9D", "#4ADE80", "#818CF8", "#FB923C", "#38BDF8", "#F2545B"];
const TOOLTIP_STYLE = { background: "#171C26", border: "1px solid #1B212C", fontSize: 12, color: "#E8EBEF" };

function sizeToSpan(size) {
  if (size === "small") return "span 3";
  if (size === "large") return "span 12";
  return "span 6";
}

function KpiCard({ kpi }) {
  const comp = kpi.comparison;
  const displayValue = kpi.formatted_value || (typeof kpi.value === "number" ? kpi.value.toLocaleString() : kpi.value);
  return (
    <div className="card kpi-tile">
      <div className="kpi-label">{kpi.label}</div>
      <div className="kpi-value mono">{displayValue}</div>
      {comp && (
        <div className={`kpi-trend ${comp.direction}`}>
          {comp.direction === "up" && <TrendingUp size={12} />}
          {comp.direction === "down" && <TrendingDown size={12} />}
          {comp.direction === "flat" && <Minus size={12} />}
          {Math.abs(comp.pct_change)}% vs {comp.previous_period}
        </div>
      )}
    </div>
  );
}

function Widget({ widget }) {
  const { type, title, size } = widget;

  if (type === "line" && widget.data?.length) {
    return (
      <div className="card" style={{ gridColumn: sizeToSpan(size) }}>
        <div className="card-title">{title}</div>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={widget.data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1B212C" />
            <XAxis dataKey="period" tick={{ fill: "#7C8798", fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: "#7C8798", fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: "#E8EBEF" }} itemStyle={{ color: "#E8EBEF" }} />
            <Line type="monotone" dataKey="value" stroke="#00D4B8" strokeWidth={2.5} dot={{ r: 3, fill: "#00D4B8" }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    );
  }

  if (type === "bar" && widget.data?.length) {
    return (
      <div className="card" style={{ gridColumn: sizeToSpan(size) }}>
        <div className="card-title">{title}</div>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={widget.data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1B212C" vertical={false} />
            <XAxis dataKey="name" tick={{ fill: "#7C8798", fontSize: 10 }} axisLine={false} tickLine={false} angle={-20} textAnchor="end" height={50} />
            <YAxis tick={{ fill: "#7C8798", fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: "#E8EBEF" }} itemStyle={{ color: "#E8EBEF" }} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
            <Bar dataKey="value" radius={[6, 6, 0, 0]}>
              {widget.data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }

  if (type === "pie" && widget.data?.length) {
    return (
      <div className="card" style={{ gridColumn: sizeToSpan(size) }}>
        <div className="card-title">{title}</div>
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie data={widget.data} dataKey="value" nameKey="name" innerRadius={45} outerRadius={78} paddingAngle={2}>
              {widget.data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
            </Pie>
            <Tooltip
              contentStyle={TOOLTIP_STYLE}
              labelStyle={{ color: "#E8EBEF" }}
              itemStyle={{ color: "#E8EBEF" }}
              formatter={(v, n, p) => [`${v} (${p.payload.pct}%)`, n]}
            />
            <Legend wrapperStyle={{ fontSize: 11, color: "#E8EBEF" }} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    );
  }

  if (type === "table" && widget.data?.length) {
    return (
      <div className="card" style={{ gridColumn: sizeToSpan(size) }}>
        <div className="card-title">{title}</div>
        <table className="dash-table">
          <tbody>
            {widget.data.map((row, i) => (
              <tr key={i}>
                <td>{row.name}</td>
                <td className="mono" style={{ textAlign: "right" }}>{row.value.toLocaleString()}</td>
                <td className="mono" style={{ textAlign: "right", color: "var(--text-dim)", width: 50 }}>{row.pct}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (type === "correlation" && widget.matrix) {
    return (
      <div className="card" style={{ gridColumn: sizeToSpan(size) }}>
        <div className="card-title">{title}</div>
        <div className="corr-grid" style={{ gridTemplateColumns: `100px repeat(${widget.columns.length}, 1fr)` }}>
          <div></div>
          {widget.columns.map((c) => <div key={c} className="corr-header mono">{c.slice(0, 8)}</div>)}
          {widget.columns.map((rowCol, ri) => (
            <div key={rowCol} style={{ display: "contents" }}>
              <div className="corr-header mono">{rowCol.slice(0, 12)}</div>
              {widget.columns.map((_, ci) => {
                const val = widget.matrix[ri][ci];
                const intensity = Math.abs(val);
                const color = val >= 0 ? `rgba(0,212,184,${intensity})` : `rgba(242,84,91,${intensity})`;
                return <div key={ci} className="corr-cell mono" style={{ background: color }}>{val.toFixed(2)}</div>;
              })}
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (type === "histogram" && widget.data?.length) {
    return (
      <div className="card" style={{ gridColumn: sizeToSpan(size) }}>
        <div className="card-title">{title}</div>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={widget.data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1B212C" vertical={false} />
            <XAxis dataKey="name" tick={{ fill: "#7C8798", fontSize: 9 }} axisLine={false} tickLine={false} angle={-30} textAnchor="end" height={45} />
            <YAxis tick={{ fill: "#7C8798", fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: "#E8EBEF" }} itemStyle={{ color: "#E8EBEF" }} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
            <Bar dataKey="value" fill="#818CF8" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }

  if (type === "scatter" && widget.data?.length) {
    return (
      <div className="card" style={{ gridColumn: sizeToSpan(size) }}>
        <div className="card-title">{title}</div>
        <ResponsiveContainer width="100%" height={240}>
          <ScatterChart>
            <CartesianGrid strokeDasharray="3 3" stroke="#1B212C" />
            <XAxis dataKey="x" type="number" tick={{ fill: "#7C8798", fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis dataKey="y" type="number" tick={{ fill: "#7C8798", fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: "#E8EBEF" }} itemStyle={{ color: "#E8EBEF" }} cursor={{ stroke: "#7C8798" }} />
            <Scatter data={widget.data} fill="#FF6B9D" fillOpacity={0.7} />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    );
  }

  return null;
}

function FullDashboard({ data }) {
  return (
    <div>
      {data.dashboard_title && (
  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
    <h2 style={{ fontSize: 19 }}>{data.dashboard_title}</h2>
    <a href={exportDashboardUrl()} target="_blank" rel="noreferrer" className="btn btn-ghost" style={{ fontSize: 12 }}>
      <Download size={13} /> Download Dashboard
    </a>
  </div>
)}
      {data.domain_reasoning && (
        <div className="ai-note" style={{ marginTop: 8 }}>
          <Sparkles size={13} color="var(--accent)" />
          <span>{data.domain_reasoning}</span>
        </div>
      )}

      {data.kpis?.length > 0 && (
        <div className="kpi-row">
          {data.kpis.map((k, i) => <KpiCard key={i} kpi={k} />)}
        </div>
      )}

      {data.anomalies?.length > 0 && (
        <div className="insight-strip">
          {data.anomalies.map((a, i) => (
            <div key={i} className="insight-chip anomaly-chip">
              <AlertTriangle size={13} color="var(--danger)" />
              <span>{a.message}</span>
            </div>
          ))}
        </div>
      )}

      <div className="widget-grid">
        {data.widgets?.map((w) => <Widget key={w.id} widget={w} />)}
      </div>
    </div>
  );
}

function Dashboard() {
  const {
    isReady, dashboardData, setDashboardData,
    tableDashboards, setTableDashboards,
  } = useDataset();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tablesLoading, setTablesLoading] = useState(false);

  useEffect(() => {
    if (!isReady || dashboardData) return;
    setLoading(true);
    setError(null);
    api.get("/dashboard-insights")
      .then((res) => setDashboardData(res.data))
      .catch((err) => setError(err.response?.data?.detail || "Failed to load dashboard."))
      .finally(() => setLoading(false));
  }, [isReady, dashboardData, setDashboardData]);

  useEffect(() => {
  if (!dashboardData?.multi_table || tableDashboards) return;
  setTablesLoading(true);
  const tables = dashboardData.tables || [];

  const loadSequentially = async () => {
    const results = [];
    for (const t of tables) {
      try {
        const res = await getTableDashboard(t);
        results.push({ table: t, data: res, error: null });
      } catch (err) {
        results.push({ table: t, data: null, error: err.response?.data?.detail || err.message });
      }
      setTableDashboards([...results]); // update progressively so tables appear as they finish
    }
    setTablesLoading(false);
  };

  loadSequentially();
}, [dashboardData, tableDashboards, setTableDashboards]);

  if (!isReady) return <div className="hero-empty"><p>Upload a dataset first.</p></div>;
  if (loading) return <div style={{ color: "var(--text-dim)", fontSize: 13 }}>Analyzing your dataset and designing a dashboard...</div>;
  if (error) return <div style={{ color: "var(--danger)", fontSize: 13 }}>{error}</div>;

  if (dashboardData?.multi_table) {
    return (
      <div>
        {tablesLoading && <div style={{ color: "var(--text-dim)", fontSize: 13, marginBottom: 16 }}>Building dashboards for {dashboardData.tables?.length || 0} tables...</div>}
        {!tablesLoading && tableDashboards?.map(({ table, data, error: tableError }) => (
          <div key={table} style={{ marginBottom: 24 }}>
            <div className="card-title" style={{ fontSize: 15, marginBottom: 10 }}><Table2 size={15} /> {table}</div>
            {data?.widgets?.length > 0 ? (
              <FullDashboard data={data} />
            ) : (
              <div style={{ color: "var(--danger)", fontSize: 12.5 }}>
                {tableError ? `Failed to build dashboard for "${table}": ${tableError}` : `Not enough structure in "${table}" for a dashboard.`}
              </div>
            )}
          </div>
        ))}
      </div>
    );
  }

  if (!dashboardData || !dashboardData.widgets || dashboardData.widgets.length === 0) {
    return <div style={{ color: "var(--text-dim)", fontSize: 13 }}>Not enough structure in this dataset to build a dashboard yet.</div>;
  }

  return <FullDashboard data={dashboardData} />;
}

export default Dashboard;