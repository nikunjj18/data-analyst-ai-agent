import { useState, useRef, useEffect } from "react";
import { Code2, Send, Lightbulb, ChevronDown, ChevronUp } from "lucide-react";
import { useDataset } from "../DatasetContext";
import { askQuestion, getChartUrl } from "../api";

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

function AskData() {
  const { dataset, isReady, conversation, setConversation } = useDataset();
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [chartUrl, setChartUrl] = useState(null);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [conversation, asking]);

  if (!isReady) {
    return <div className="hero-empty"><p>Upload a dataset first.</p></div>;
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
          chartGenerated: data.chart_generated,
          time: new Date(),
        },
      ]);
      if (data.chart_generated) setChartUrl(getChartUrl());
    } catch (err) {
      setConversation((prev) => [...prev, { role: "error", text: err.response?.data?.detail || "Something went wrong.", time: new Date() }]);
    } finally {
      setAsking(false);
    }
  };

  const timeStr = (d) => d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 300px", gap: 20, height: "calc(100vh - 140px)" }}>
      <div style={{ display: "flex", flexDirection: "column", background: "var(--panel)", border: "1px solid var(--border)", borderRadius: "var(--radius)", overflow: "hidden" }}>
        <div style={{ flex: 1, overflowY: "auto", padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>
          {conversation.length === 0 && (
            <div style={{ margin: "auto", textAlign: "center" }}>
              <p style={{ color: "var(--text-dim)", fontSize: 13, marginBottom: 14 }}>Ask something about your data</p>
              <div style={{ display: "flex", flexDirection: "column", gap: 8, maxWidth: 320 }}>
                {generateSuggestedQuestions(dataset.columns).map((q, i) => (
                  <button key={i} className="btn btn-ghost" style={{ textAlign: "left", justifyContent: "flex-start" }} onClick={() => submitQuestion(q)}>
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {conversation.map((msg, i) => (
            <div key={i} style={{ display: "flex", justifyContent: msg.role === "user" ? "flex-end" : "flex-start" }}>
              {msg.role === "user" && (
                <div style={{ maxWidth: "75%", background: "#1F2937", padding: "12px 16px", borderRadius: "12px 12px 4px 12px", fontSize: 13.5 }}>
                  {msg.text}
                  <div style={{ fontSize: 10, color: "var(--text-dim)", marginTop: 6 }}>{timeStr(msg.time)}</div>
                </div>
              )}
              {msg.role === "agent" && (
                <div style={{ maxWidth: "85%", background: "var(--accent-dim)", padding: "12px 16px", borderRadius: "12px 12px 12px 4px" }}>
                  <p className="mono" style={{ fontSize: 13, whiteSpace: "pre-wrap" }}>{msg.text}</p>

                  {msg.explanation && (
                    <div style={{ display: "flex", gap: 8, marginTop: 10, padding: 10, background: "var(--panel-alt)", borderRadius: 6, borderLeft: "2px solid var(--warn)" }}>
                      <Lightbulb size={13} color="var(--warn)" style={{ flexShrink: 0, marginTop: 1 }} />
                      <p style={{ fontSize: 12, color: "var(--text-dim)", lineHeight: 1.5 }}>{msg.explanation}</p>
                    </div>
                  )}

                  {msg.code && <CodeToggle code={msg.code} attempts={msg.attempts} />}

                  <div style={{ fontSize: 10, color: "var(--text-dim)", marginTop: 8 }}>{timeStr(msg.time)}</div>
                </div>
              )}
              {msg.role === "error" && (
                <div style={{ background: "var(--danger-dim)", border: "1px solid var(--danger)", color: "var(--danger)", padding: "10px 14px", borderRadius: 8, fontSize: 13 }}>
                  {msg.text}
                </div>
              )}
            </div>
          ))}

          {asking && (
            <div style={{ display: "flex", gap: 4, padding: "12px 16px", background: "var(--accent-dim)", borderRadius: "12px 12px 12px 4px", width: "fit-content" }}>
              <span className="dot"></span><span className="dot"></span><span className="dot"></span>
            </div>
          )}
          <div ref={endRef} />
        </div>

        <form
          onSubmit={(e) => { e.preventDefault(); submitQuestion(question); }}
          style={{ display: "flex", gap: 10, padding: 14, borderTop: "1px solid var(--border)" }}
        >
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. What is total revenue by category?"
            disabled={asking}
            style={{ flex: 1, background: "var(--bg)", border: "1px solid var(--border)", borderRadius: 8, padding: "12px 14px", color: "var(--text)", fontSize: 13.5 }}
          />
          <button type="submit" className="btn btn-primary" disabled={asking || !question.trim()} style={{ width: 44, justifyContent: "center" }}>
            <Send size={15} />
          </button>
        </form>
      </div>

      <div className="card" style={{ alignSelf: "start", position: "sticky", top: 0 }}>
        <div className="card-title">Chart</div>
        {chartUrl ? (
          <img src={chartUrl} alt="Generated chart" style={{ width: "100%", borderRadius: 8, border: "1px solid var(--border)" }} />
        ) : (
          <p style={{ fontSize: 12, color: "var(--text-dim)" }}>A chart will appear here once your question produces a visual result.</p>
        )}
      </div>
    </div>
  );
}

export default AskData;