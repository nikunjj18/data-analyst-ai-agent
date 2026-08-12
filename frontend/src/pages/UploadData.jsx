import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Upload, CheckCircle2, ArrowRight, Table2, Sparkles, Brain, MessageSquareText, FileDown } from "lucide-react";
import { useDataset } from "../DatasetContext";
import { uploadFile } from "../api";

function UploadData() {
  const {
    dataset, setDataset,
    setQualityReport,
    cleaningActions, setCleaningActions,
    resetForNewDataset,
  } = useDataset();
  const [uploading, setUploading] = useState(false);
  const [preview, setPreview] = useState([]);
  const [tablePreviews, setTablePreviews] = useState({});
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    setDataset(null);
    setPreview([]);
    setTablePreviews({});
    resetForNewDataset();
    try {
      const data = await uploadFile(file);
      setQualityReport(data.quality_report);
      setCleaningActions(data.cleaning_actions || []);
      setPreview(data.preview || []);
      setTablePreviews(data.table_previews || {});
      setDataset({
        name: file.name,
        mode: data.mode,
        rows: data.rows,
        columns: data.columns,
        tables: data.tables || [],
      });
    } catch (err) {
      alert("Upload failed: " + (err.response?.data?.detail || err.message));
    } finally {
      setUploading(false);
    }
  };

  if (dataset) {
    return (
      <div>
        <div className="card" style={{ marginBottom: 16 }}>
          <h2 className="card-title"><Table2 size={14} /> Dataset ready</h2>
          <p style={{ fontSize: 13, color: "var(--text-dim)", marginBottom: 14 }}>
            {dataset.mode === "multi"
              ? `${dataset.name} loaded with ${dataset.tables.length} tables.`
              : `${dataset.name} loaded with ${dataset.rows.toLocaleString()} rows and ${dataset.columns.length} columns.`}
          </p>

          {dataset.mode === "multi" ? (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 18 }}>
              {dataset.tables.map((t) => (
                <span key={t} className="mono" style={{ background: "var(--accent-dim)", color: "var(--accent)", padding: "4px 9px", borderRadius: 6, fontSize: 11.5 }}>
                  {t}
                </span>
              ))}
            </div>
          ) : (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 18 }}>
              {dataset.columns.map((c) => (
                <span key={c} className="mono" style={{ background: "var(--accent-dim)", color: "var(--accent)", padding: "4px 9px", borderRadius: 6, fontSize: 11.5 }}>
                  {c}
                </span>
              ))}
            </div>
          )}

          <div style={{ display: "flex", gap: 10 }}>
            <button className="btn btn-ghost" onClick={() => fileInputRef.current.click()}>
              Upload different file
            </button>
            <button
              className="btn btn-primary"
              onClick={() => navigate(dataset.mode === "multi" ? "/ask" : "/dashboard")}
            >
              {dataset.mode === "multi" ? "Ask Your Data" : "Go to Dashboard"} <ArrowRight size={14} />
            </button>
            <input ref={fileInputRef} type="file" accept=".csv,.xlsx,.xls,.zip" onChange={handleFileUpload} hidden />
          </div>
        </div>

        {cleaningActions.length > 0 && (
          <div className="card" style={{ marginBottom: 16 }}>
            <h2 className="card-title"><CheckCircle2 size={14} color="var(--success)" /> Data cleaning applied automatically</h2>
            <p style={{ fontSize: 12, color: "var(--text-dim)", marginBottom: 12 }}>
              The agent detected and resolved these issues before analysis began:
            </p>
            <ul style={{ paddingLeft: 18, fontSize: 12.5, lineHeight: 1.9 }}>
              {cleaningActions.map((action, i) => <li key={i}>{action}</li>)}
            </ul>
          </div>
        )}

        {dataset.mode !== "multi" && preview.length > 0 && (
          <div className="card">
            <h2 className="card-title"><Table2 size={14} /> Preview (first 5 rows, after cleaning)</h2>
            <div style={{ overflowX: "auto" }}>
              <table className="preview-table">
                <thead>
                  <tr>
                    {dataset.columns.map((c) => <th key={c} className="mono">{c}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {preview.map((row, i) => (
                    <tr key={i}>
                      {dataset.columns.map((c) => <td key={c} className="mono">{row[c]}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {dataset.mode === "multi" && Object.keys(tablePreviews).length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {Object.entries(tablePreviews).map(([tableName, preview]) => (
              <div key={tableName} className="card">
                <h2 className="card-title"><Table2 size={14} /> {tableName} (first 5 rows)</h2>
                <div style={{ overflowX: "auto" }}>
                  <table className="preview-table">
                    <thead>
                      <tr>
                        {preview.columns.map((c) => <th key={c} className="mono">{c}</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {preview.rows.map((row, i) => (
                        <tr key={i}>
                          {preview.columns.map((c) => <td key={c} className="mono">{row[c]}</td>)}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="landing">
      <div className="landing-hero">
        <div className="landing-eyebrow"><Sparkles size={12} /> AI Data Analyst</div>
        <h2>Turn any spreadsheet into<br /><span>a conversation</span></h2>
        <p>
          Upload a dataset and ask questions in plain English. The agent cleans your data,
          writes real code, explains its reasoning, and shows you the answer, with a chart and a full report.
        </p>
      </div>

      <div className="feature-row">
        <div className="feature-card">
          <div className="feature-card-icon"><Brain size={17} /></div>
          <h4>Automatic Data Cleaning</h4>
          <p>Detects and fixes missing values and issues automatically, then tells you exactly what it did.</p>
        </div>
        <div className="feature-card">
          <div className="feature-card-icon"><MessageSquareText size={17} /></div>
          <h4>Plain-English Q&A</h4>
          <p>Ask anything about your data, single table or multiple related ones in a zip.</p>
        </div>
        <div className="feature-card">
          <div className="feature-card-icon"><FileDown size={17} /></div>
          <h4>Instant Reports</h4>
          <p>Auto-generated charts and a downloadable PDF summary of your full analysis.</p>
        </div>
      </div>

      <div className="upload-drop-large" onClick={() => fileInputRef.current.click()}>
        <div className="icon-circle"><Upload size={22} /></div>
        <p>{uploading ? "Uploading and cleaning your data..." : "Click to upload a file"}</p>
        <span>.csv, .xlsx, .xls, or .zip (multiple tables) supported</span>
        <input ref={fileInputRef} type="file" accept=".csv,.xlsx,.xls,.zip" onChange={handleFileUpload} hidden />
      </div>
    </div>
  );
}

export default UploadData;