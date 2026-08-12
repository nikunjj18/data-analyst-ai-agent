import { useEffect, useState } from "react";
import { FileDown, Sparkles, RefreshCw, Download } from "lucide-react";
import { useDataset } from "../DatasetContext";
import { getInsights, exportReportUrl } from "../api";

function ExportReport() {
  const { dataset, qualityReport, conversation, isReady } = useDataset();
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadInsights = () => {
    setLoading(true);
    getInsights()
      .then((data) => setInsights(data.insights))
      .catch(() => setInsights("Could not generate insights right now."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (isReady) loadInsights();
  }, [isReady]);

  if (!isReady) {
    return <div className="hero-empty"><p>Upload a dataset first.</p></div>;
  }

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
        ) : (
          <p style={{ fontSize: 13.5, lineHeight: 1.7 }}>{insights}</p>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
        <div className="card">
          <div className="card-title">Dataset</div>
          <p style={{ fontSize: 13 }}>{dataset.name}</p>
          <p className="mono" style={{ fontSize: 12, color: "var(--text-dim)", marginTop: 4 }}>
            {dataset.rows.toLocaleString()} rows · {dataset.columns.length} columns
          </p>
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
        <p style={{ fontSize: 12.5, color: "var(--text-dim)", marginBottom: 18, maxWidth: 380, margin: "0 auto 18px" }}>
          Includes dataset overview, data quality summary, your full Q&A conversation with
          generated code, and the latest chart.
        </p>
        <a href={exportReportUrl()} target="_blank" rel="noreferrer" className="btn btn-primary" style={{ display: "inline-flex" }}>
          <Download size={14} /> Download PDF Report
        </a>
      </div>
    </div>
  );
}

export default ExportReport;