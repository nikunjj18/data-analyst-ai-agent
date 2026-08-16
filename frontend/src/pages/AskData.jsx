import { useState, useRef, useEffect } from "react";
import { Code2, Send, Lightbulb, ChevronDown, ChevronUp, Download } from "lucide-react";
import { useDataset } from "../DatasetContext";
import { askQuestion, getChartUrlById } from "../api";

function generateSuggestedQuestions(columns) {
  const numericHints = ["price", "revenue", "quantity", "amount", "cost", "total", "sales"];
  const categoryHints = ["category", "region", "segment", "product", "type", "status"];
  const numericCol = columns.find((c) => numericHints.some((h) => c.toLowerCase().includes(h)));
  const categoryCol = columns.find((c) => categoryHints.some((h) => c.toLowerCase().includes(h)));
  const s = [];
  if (numericCol) s.push(`What is the total ${numericCol.replace(/_/g, " ")}?`);
  if (numericCol && categoryCol) s.push(`What is the total ${numericCol.replace(/_/g, " ")} by ${categoryCol.replace(/_/g, " ")}?`);
  if (categoryCol) s.push(`How many unique ${categoryCol.replace(/_/g, " ")} are there?`);
  s.push("Is the data clean or not?");
  return s.slice(0, 4);
}

function CodeToggle({ code, attempts }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ marginTop: 10, border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden" }}>
      <button
        onClick={() => setOpen(!open)}
        style={{ display: "flex", alignItems: "center", gap: 6, width: "100%", padding: "8px 12px", fontSize: 11.5, color: "var(--text-dim)", background: "rgba(255,255,255,0.02)" }}
      >
        <Code2 size={12} /> {open ? "Hide" : "Show"} generated code {attempts > 1 && `(${attempts} attempts)`}
        {open ? <ChevronUp size={12} style={{ marginLeft: "auto" }} /> : <ChevronDown size={12} style={{ marginLeft: "auto" }} />}
      </button>
      {open && (
        <pre className="mono" style={{ margin: 0, padding: 12, fontSize: 11.5, background: "#0A0D12", color: "#7ee787", overflowX: "auto" }}>
          {code}
        </pre>
      )}
    </div>
  );
}

function InlineChart({ chartId, question }) {
  const url = getChartUrlById(chartId);

  const handleDownload = async () => {
    const response = await fetch(url);
    const blob = await response.blob();
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `chart-${question.slice(0, 30).replace(/\s+/g, "_")}.png`;
    link.click();
  };

  return (
    <div style={{ marginTop: 10 }}>
      <img src={url} alt="Generated chart" className="chart-image-inline" />
      <button className="btn btn-ghost" onClick={handleDownload} style={{ marginTop: 8, fontSize: 11.5 }}>
        <Download size={12} /> Download chart
      </button>
    </div>
  );
}

function AskData() {
  const { dataset, isReady, conversation, setConversation } = useDataset();
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [conversation, asking]);

  if (!isReady) {
    return <div className="hero-empty" style={{ paddingTop: 60 }}><p>Upload a dataset first.</p></div>;
  }

  const submitQuestion = async (q) => {
    if (!q.trim()) return;
    setQuestion("");
    setAsking(true);
    setConversation((prev) => [...prev, { role: "user", text: q, time: new Date() }]);

    try {
      const data = await askQuestion(q);
      setConversation((prev) => [
        ...prev,
        {
          role: "agent",
          text: data.result,
          explanation: data.explanation,
          code: data.code,
          attempts: data.attempts,
          chartId: data.chart_id,
          question: q,
          time: new Date(),
        },
      ]);
    } catch (err) {
      setConversation((prev) => [...prev, { role: "error", text: err.response?.data?.detail || "Something went wrong.", time: new Date() }]);
    } finally {
      setAsking(false);
    }
  };

  const timeStr = (d) => d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  return (
    <div className="chat-fullscreen">
      <div className="chat-scroll">
        <div className="chat-inner">
          {conversation.length === 0 && (
            <div style={{ margin: "auto", textAlign: "center", paddingTop: 60 }}>
              <p style={{ color: "var(--text-dim)", fontSize: 14, marginBottom: 16 }}>Ask something about your data</p>
              <div style={{ display: "flex", flexDirection: "column", gap: 8, maxWidth: 360, margin: "0 auto" }}>
                {generateSuggestedQuestions(dataset.columns).map((q, i) => (
                  <button key={i} className="btn btn-ghost" style={{ textAlign: "left", justifyContent: "flex-start" }} onClick={() => submitQuestion(q)}>
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {conversation.map((msg, i) => (
            <div key={i} style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 20 }}>
              {msg.role === "user" && (
                <div style={{ alignSelf: "flex-end", maxWidth: "80%", background: "#1F2937", padding: "12px 16px", borderRadius: "14px 14px 4px 14px", fontSize: 14.5, fontWeight: 500 }}>
                  {msg.text}
                  <div style={{ fontSize: 10, color: "var(--text-dim)", marginTop: 6, textAlign: "right" }}>{timeStr(msg.time)}</div>
                </div>
              )}
              {msg.role === "agent" && (
                <div style={{ alignSelf: "flex-start", maxWidth: "100%", width: "100%", background: "var(--panel)", border: "1px solid var(--border)", padding: "16px 18px", borderRadius: 14 }}>
                  <p className="mono" style={{ fontSize: 14, whiteSpace: "pre-wrap" }}>{msg.text}</p>

                  {msg.explanation && (
                    <div style={{ display: "flex", gap: 8, marginTop: 12, padding: 12, background: "var(--panel-alt)", borderRadius: 8, borderLeft: "2px solid var(--warn)" }}>
                      <Lightbulb size={14} color="var(--warn)" style={{ flexShrink: 0, marginTop: 1 }} />
                      <p style={{ fontSize: 13, color: "var(--text-dim)", lineHeight: 1.55 }}>{msg.explanation}</p>
                    </div>
                  )}

                  {msg.chartId && <InlineChart chartId={msg.chartId} question={msg.question} />}
                  {msg.code && <CodeToggle code={msg.code} attempts={msg.attempts} />}

                  <div style={{ fontSize: 10, color: "var(--text-dim)", marginTop: 10 }}>{timeStr(msg.time)}</div>
                </div>
              )}
              {msg.role === "error" && (
                <div style={{ alignSelf: "flex-start", background: "var(--danger-dim)", border: "1px solid var(--danger)", color: "var(--danger)", padding: "10px 14px", borderRadius: 8, fontSize: 13 }}>
                  {msg.text}
                </div>
              )}
            </div>
          ))}

          {asking && (
            <div style={{ display: "flex", gap: 4, padding: "12px 16px", background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 14, width: "fit-content" }}>
              <span className="dot"></span><span className="dot"></span><span className="dot"></span>
            </div>
          )}
          <div ref={endRef} />
        </div>
      </div>

      <div className="chat-input-bar">
        <form onSubmit={(e) => { e.preventDefault(); submitQuestion(question); }} className="chat-inner" style={{ display: "flex", gap: 10 }}>
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Message your data..."
            disabled={asking}
            style={{ flex: 1, background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 24, padding: "13px 18px", color: "var(--text)", fontSize: 14.5 }}
          />
          <button type="submit" className="btn btn-primary" disabled={asking || !question.trim()} style={{ width: 46, height: 46, borderRadius: "50%", justifyContent: "center", padding: 0 }}>
            <Send size={17} />
          </button>
        </form>
      </div>
    </div>
  );
}

export default AskData;