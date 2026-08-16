import { useEffect, useState } from "react";
import { FileDown, Sparkles, RefreshCw, Download, Table2 } from "lucide-react";
import { useDataset } from "../DatasetContext";
import { getInsights, exportReportUrl } from "../api";

function ExportReport() {
  const { dataset, conversation, isReady } = useDataset();
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadInsights = () => {
    setLoading(true);
    setError(null);
    getInsights()
      .then((data) => setInsights(data.insights))
      .catch((err) => setError(err.response?.data?.detail || "Could not generate insights right now."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (isReady) loadInsights();
  }, [isReady]);

  if (!isReady) {
    return <div className="hero-empty"><p>Upload a dataset first.</p></div>;
  }

  const isMulti = dataset.mode === "multi";

  return (
    <div>
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-title">
          <Sparkles size={14} color="var(--accent)" /> AI-Generated Executive Summary
          <button
            onClick={loadInsights}
            style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 4, fontSize: 11, color: "var(--text-dim)" }}
          >
            <RefreshCw size={12} className={loading ? "spin" : ""} /> Regenerate
          </button>
        </div>
        {loading ? (
          <p style={{ fontSize: 13, color: "var(--text-dim)" }}>Analyzing dataset...</p>
        ) : error ? (
          <p style={{ fontSize: 13, color: "var(--danger)" }}>{error}</p>
        ) : (
          <p style={{ fontSize: 13.5, lineHeight: 1.7 }}>{insights}</p>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
        <div className="card">
          <div className="card-title">Dataset</div>
          <p style={{ fontSize: 13 }}>{dataset.name}</p>
          {isMulti ? (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
              {dataset.tables.map((t) => (
                <span key={t} className="mono" style={{ background: "var(--accent-dim)", color: "var(--accent)", padding: "3px 8px", borderRadius: 5, fontSize: 11 }}>
                  <Table2 size={10} style={{ marginRight: 3, verticalAlign: "middle" }} />{t}
                </span>
              ))}
            </div>
          ) : (
            <p className="mono" style={{ fontSize: 12, color: "var(--text-dim)", marginTop: 4 }}>
              {dataset.rows?.toLocaleString()} rows &middot; {dataset.columns.length} columns
            </p>
          )}
        </div>
        <div className="card">
          <div className="card-title">Questions Analyzed</div>
          <p className="mono" style={{ fontSize: 28, fontWeight: 700, color: "var(--accent)" }}>
            {conversation.filter((m) => m.role === "user").length}
          </p>
        </div>
      </div>

      <div className="card" style={{ textAlign: "center", padding: 32 }}>
        <FileDown size={28} color="var(--accent)" style={{ marginBottom: 10 }} />
        <h3 style={{ fontSize: 15, marginBottom: 6 }}>Full PDF Report</h3>
        <p style={{ fontSize: 12.5, color: "var(--text-dim)", marginBottom: 18, maxWidth: 420, margin: "0 auto 18px" }}>
          {isMulti
            ? `Includes a preview, summary, and dashboard for each of the ${dataset.tables.length} tables, plus your full Q&A conversation with charts.`
            : "Includes dataset preview, data quality, features, AI summary, dashboard with charts, and your full Q&A conversation with charts."}
        </p>
        <a href={exportReportUrl()} target="_blank" rel="noreferrer" className="btn btn-primary" style={{ display: "inline-flex" }}>
          <Download size={14} /> Download PDF Report
        </a>
        {isMulti && (
          <p style={{ fontSize: 11, color: "var(--text-faint)", marginTop: 12 }}>
            This may take up to a minute for datasets with several tables.
          </p>
        )}
      </div>
    </div>
  );
}

export default ExportReport;