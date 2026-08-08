import { useState, useRef } from "react";
import { uploadFile, askQuestion, getChartUrl } from "./api";
import "./App.css";

function App() {
  const [dataset, setDataset] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [conversation, setConversation] = useState([]);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [chartUrl, setChartUrl] = useState(null);
  const fileInputRef = useRef(null);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    try {
      const data = await uploadFile(file);
      setDataset({ name: file.name, rows: data.rows, columns: data.columns });
      setConversation([]);
      setChartUrl(null);
    } catch (err) {
      alert("Upload failed: " + (err.response?.data?.detail || err.message));
    } finally {
      setUploading(false);
    }
  };

  const handleAsk = async (e) => {
    e.preventDefault();
    if (!question.trim() || !dataset) return;

    const currentQuestion = question;
    setQuestion("");
    setAsking(true);
    setConversation((prev) => [...prev, { role: "user", text: currentQuestion }]);

    try {
      const data = await askQuestion(currentQuestion);
      setConversation((prev) => [
        ...prev,
        { role: "agent", text: data.result, code: data.code, attempts: data.attempts },
      ]);
      if (data.chart_generated) {
        setChartUrl(getChartUrl());
      } else {
        setChartUrl(null);
      }
    } catch (err) {
      setConversation((prev) => [
        ...prev,
        { role: "error", text: err.response?.data?.detail || "Something went wrong." },
      ]);
    } finally {
      setAsking(false);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-mark">⌗</div>
        <div>
          <h1>Data Analyst Agent</h1>
          <p className="header-sub">Ask questions. Get real answers, backed by code.</p>
        </div>
      </header>

      <div className="workspace">
        <aside className="sidebar">
          <div className="panel">
            <h2>Dataset</h2>
            {!dataset ? (
              <div className="upload-zone" onClick={() => fileInputRef.current.click()}>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv"
                  onChange={handleFileUpload}
                  hidden
                />
                <span className="upload-icon">↑</span>
                <p>{uploading ? "Uploading..." : "Click to upload a CSV"}</p>
              </div>
            ) : (
              <div className="dataset-info">
                <p className="dataset-name">{dataset.name}</p>
                <p className="dataset-meta">{dataset.rows.toLocaleString()} rows · {dataset.columns.length} columns</p>
                <div className="column-tags">
                  {dataset.columns.map((c) => (
                    <span key={c} className="col-tag">{c}</span>
                  ))}
                </div>
                <button className="reset-btn" onClick={() => fileInputRef.current.click()}>
                  Upload different file
                </button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv"
                  onChange={handleFileUpload}
                  hidden
                />
              </div>
            )}
          </div>

          {chartUrl && (
            <div className="panel">
              <h2>Chart</h2>
              <img src={chartUrl} alt="Generated chart" className="chart-image" />
            </div>
          )}
        </aside>

        <main className="chat-area">
          <div className="messages">
            {conversation.length === 0 && (
              <div className="empty-state">
                <p>{dataset ? "Ask something about your data." : "Upload a CSV to get started."}</p>
              </div>
            )}
            {conversation.map((msg, i) => (
              <div key={i} className={`message message-${msg.role}`}>
                {msg.role === "user" && <div className="bubble user-bubble">{msg.text}</div>}
                {msg.role === "agent" && (
                  <div className="bubble agent-bubble">
                    <p className="result-text">{msg.text}</p>
                    {msg.code && (
                      <details className="code-detail">
                        <summary>View generated code {msg.attempts > 1 && `(${msg.attempts} attempts)`}</summary>
                        <pre>{msg.code}</pre>
                      </details>
                    )}
                  </div>
                )}
                {msg.role === "error" && <div className="bubble error-bubble">{msg.text}</div>}
              </div>
            ))}
            {asking && <div className="bubble agent-bubble thinking">Thinking…</div>}
          </div>

          <form className="ask-form" onSubmit={handleAsk}>
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder={dataset ? "e.g. What is total revenue by category?" : "Upload a dataset first"}
              disabled={!dataset || asking}
            />
            <button type="submit" disabled={!dataset || asking || !question.trim()}>
              Ask
            </button>
          </form>
        </main>
      </div>
    </div>
  );
}

export default App;