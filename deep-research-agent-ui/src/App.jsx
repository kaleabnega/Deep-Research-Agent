import { useMemo, useState } from "react";

const SOURCE_TYPES = [
  { id: "peer_reviewed", label: "Peer-reviewed" },
  { id: "preprint", label: "Preprint" },
  { id: "news", label: "News" },
  { id: "encyclopedia", label: "Encyclopedia" },
  { id: "blog", label: "Blog" },
  { id: "other", label: "Other" }
];

export default function App() {
  const [question, setQuestion] = useState("");
  const [startYear, setStartYear] = useState("2020");
  const [endYear, setEndYear] = useState("2025");
  const [selectedSources, setSelectedSources] = useState(["peer_reviewed"]);
  const [files, setFiles] = useState([]);
  const [report, setReport] = useState("");
  const [mode, setMode] = useState("briefing");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const constraints = useMemo(() => {
    return {
      source_types: selectedSources,
      time_range: {
        start_year: Number(startYear) || undefined,
        end_year: Number(endYear) || undefined
      }
    };
  }, [selectedSources, startYear, endYear]);

  const toggleSource = (id) => {
    setSelectedSources((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setReport("");
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append("question", question.trim());
      formData.append("mode", mode);
      formData.append("constraints", JSON.stringify(constraints));
      files.forEach((file) => formData.append("files", file));

      const res = await fetch("http://127.0.0.1:8000/research", {
        method: "POST",
        body: formData
      });

      if (!res.ok) {
        throw new Error(`Server error: ${res.status}`);
      }

      const data = await res.json();
      setReport(data.report || "No report returned.");
    } catch (err) {
      setError(err.message || "Request failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <header className="hero">
        <nav className="nav">
          <div className="logo">Deep Research</div>
          <div className="pill">Agentic Briefing</div>
        </nav>
        <div className="hero-content">
          <h1>Deep Research Agent</h1>
          <p>
            Plan. Execute. Reflect. Build evidence-backed briefings with constraints,
            citations, and file-aware context.
          </p>
        </div>
      </header>

      <main className="grid">
        <section className="card">
          {/* <h2>Research Query</h2>
          <p className="muted">Connects to your FastAPI endpoint.</p> */}
          <form onSubmit={handleSubmit} className="form">
            <label className="field">
              <span>Question</span>
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask a deep research question..."
                required
              />
            </label>

            <label className="field">
              <span>Mode</span>
              <select value={mode} onChange={(e) => setMode(e.target.value)} >
                <option value="briefing">Briefing</option>
                <option value="essay">Essay</option>
              </select>
            </label>

            <div className="row">
              <label className="field">
                <span>Start year</span>
                <input
                  type="number"
                  value={startYear}
                  onChange={(e) => setStartYear(e.target.value)}
                />
              </label>
              <label className="field">
                <span>End year</span>
                <input
                  type="number"
                  value={endYear}
                  onChange={(e) => setEndYear(e.target.value)}
                />
              </label>
            </div>

            <div className="field">
              <span>Source types</span>
              <div className="chips">
                {SOURCE_TYPES.map((source) => (
                  <button
                    type="button"
                    key={source.id}
                    className={
                      selectedSources.includes(source.id)
                        ? "chip active"
                        : "chip"
                    }
                    onClick={() => toggleSource(source.id)}
                  >
                    {source.label}
                  </button>
                ))}
              </div>
            </div>

            <label className="field">
              <span>Upload files</span>
              <input
                type="file"
                multiple
                onChange={(e) => setFiles(Array.from(e.target.files || []))}
              />
            </label>

            <button type="submit" className="primary" disabled={loading}>
              {loading ? "Running research..." : "Generate"}
            </button>
            {error && <div className="error">{error}</div>}
          </form>
        </section>

        <section className="card output">
          {/* <h2>Briefing Output</h2> */}
          <p className="muted">Results stream here when the run completes.</p>
          <div className="report">
            {report ? <pre>{report}</pre> : <div className="empty">No report yet.</div>}
          </div>
        </section>
      </main>
    </div>
  );
}
