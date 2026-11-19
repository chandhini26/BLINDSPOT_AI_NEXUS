import React, { useEffect, useMemo, useState } from "react";
import "./App.css";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function App() {
  const [token, setToken] = useState(localStorage.getItem("blindspot_token") || "");
  const [user, setUser] = useState(null);
  const [authMode, setAuthMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authBusy, setAuthBusy] = useState(false);
  const [authError, setAuthError] = useState("");
  const [backend, setBackend] = useState("checking");

  const [page, setPage] = useState("Dashboard");
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState("");
  const [file, setFile] = useState(null);
  const [projectName, setProjectName] = useState("");
  const [uploadBusy, setUploadBusy] = useState(false);
  const [busyProject, setBusyProject] = useState("");
  const [selectedProject, setSelectedProject] = useState(null);
  const [report, setReport] = useState(null);
  const [chatProject, setChatProject] = useState(null);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [chatBusy, setChatBusy] = useState(false);
  const [chatError, setChatError] = useState("");
  const [compareIds, setCompareIds] = useState([]);

  async function apiFetch(path, options = {}) {
    const headers = { ...(options.headers || {}) };
    if (token) headers.Authorization = `Bearer ${token}`;
    if (options.body && !(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }
    const response = await fetch(`${API}${path}`, { ...options, headers });
    if (!response.ok) {
      let message = `Request failed (${response.status})`;
      try {
        const data = await response.json();
        message = data.detail || data.message || message;
      } catch {}
      throw new Error(message);
    }
    const type = response.headers.get("content-type") || "";
    return type.includes("application/pdf") ? response.blob() : response.json();
  }

  async function loadProjects() {
    if (!token) return;
    setLoading(true);
    try {
      const data = await apiFetch("/projects");
      setProjects(Array.isArray(data) ? data : []);
    } catch (error) {
      setNotice(error.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetch(`${API}/health`)
      .then((r) => r.ok ? r.json() : Promise.reject())
      .then(() => setBackend("online"))
      .catch(() => setBackend("offline"));
  }, []);

  useEffect(() => {
    if (!token) {
      setUser(null);
      return;
    }
    apiFetch("/auth/me")
      .then(setUser)
      .catch(() => {
        localStorage.removeItem("blindspot_token");
        setToken("");
        setUser(null);
      });
  }, [token]);

  useEffect(() => {
    if (user) loadProjects();
  }, [user]);

  async function authenticate(event) {
    event.preventDefault();
    setAuthError("");
    setAuthBusy(true);
    try {
      const endpoint = authMode === "login" ? "/auth/login" : "/auth/register";
      const data = await fetch(`${API}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      }).then(async (r) => {
        const d = await r.json();
        if (!r.ok) throw new Error(d.detail || "Authentication failed");
        return d;
      });
      localStorage.setItem("blindspot_token", data.access_token);
      setToken(data.access_token);
      setUser(data.user);
    } catch (error) {
      setAuthError(error.message);
    } finally {
      setAuthBusy(false);
    }
  }

  function logout() {
    localStorage.removeItem("blindspot_token");
    setToken("");
    setUser(null);
    setProjects([]);
    setChatProject(null);
    setReport(null);
    setPage("Dashboard");
  }

  async function uploadProject(event) {
    event.preventDefault();
    if (!file) return setNotice("Please choose a PDF, DOCX or TXT file.");
    setUploadBusy(true);
    setNotice("");
    const body = new FormData();
    body.append("file", file);
    body.append("project_name", projectName);
    try {
      const result = await apiFetch("/projects/upload", { method: "POST", body });
      setNotice(`Uploaded successfully. ${result.chunks_indexed} text sections indexed.`);
      setFile(null);
      setProjectName("");
      event.target.reset();
      await loadProjects();
      setPage("Project analysis");
    } catch (error) {
      setNotice(error.message);
    } finally {
      setUploadBusy(false);
    }
  }

  async function analyzeProject(project) {
    setBusyProject(project.id);
    setNotice("");
    try {
      const result = await apiFetch(`/projects/${project.id}/analyze`, { method: "POST" });
      setSelectedProject(project);
      setReport(result);
      setPage("Project analysis");
      setNotice("AI project analysis completed.");
      await loadProjects();
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusyProject("");
    }
  }

  async function viewReport(project) {
    try {
      const result = await apiFetch(`/projects/${project.id}/report`);
      setSelectedProject(project);
      setReport(result);
      setPage("Project analysis");
      setNotice("");
    } catch (error) {
      setNotice(error.message);
    }
  }

  async function downloadPdf(project) {
    try {
      const blob = await apiFetch(`/projects/${project.id}/report.pdf`);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "blindspot_report.pdf";
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      setNotice(error.message);
    }
  }

  async function openChat(project) {
    setChatProject(project);
    setChatError("");
    try {
      const data = await apiFetch(`/projects/${project.id}/chat/history`);
      setChatMessages(data.history || []);
      setPage("AI Chat Assistant");
    } catch (error) {
      setChatError(error.message);
      setChatMessages([]);
      setPage("AI Chat Assistant");
    }
  }

  async function sendChat(event) {
    event.preventDefault();
    if (!chatProject || !chatInput.trim()) return;
    const question = chatInput.trim();
    setChatInput("");
    setChatMessages((old) => [...old, { role: "user", message: question }]);
    setChatBusy(true);
    setChatError("");
    try {
      const data = await apiFetch(`/projects/${chatProject.id}/chat`, {
        method: "POST",
        body: JSON.stringify({ message: question })
      });
      setChatMessages((old) => [...old, {
        role: "assistant",
        message: data.answer,
        sources: data.sources || []
      }]);
    } catch (error) {
      setChatError(error.message);
    } finally {
      setChatBusy(false);
    }
  }

  const analyzedCount = projects.filter((p) => p.status === "Analyzed").length;
  const pendingCount = projects.length - analyzedCount;
  const selectedProjects = projects.filter((p) => compareIds.includes(p.id));
  const findings = Array.isArray(report?.findings) ? report.findings : [];
  const severityCount = (level) => findings.filter((f) =>
    String(f.severity || f.risk_level || "").toLowerCase().includes(level)
  ).length;

  const navItems = [
    ["Dashboard", "grid-2x2"],
    ["Project analysis", "scan-search"],
    ["History", "history"],
    ["AI Chat Assistant", "messages-square"]
  ];

  if (!user) {
    return (
      <div className="auth-screen">
        <div className="auth-art">
          <div className="brand-mark">B</div>
          <p className="eyebrow">INTELLIGENT PROJECT REVIEW</p>
          <h1>See the risks<br /><span>before they happen.</span></h1>
          <p className="muted-light">Analyze project documents, identify blind spots and ask questions using your project evidence.</p>
          <div className="auth-points"><span>✓ AI-powered review</span><span>✓ Evidence-based chat</span><span>✓ Downloadable reports</span></div>
        </div>
        <form className="auth-card" onSubmit={authenticate}>
          <div className="small-brand">BLINDSPOT <b>AI</b></div>
          <h2>{authMode === "login" ? "Welcome back" : "Create your account"}</h2>
          <p className="muted">Sign in to continue to your workspace.</p>
          <label>Email address</label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" required />
          <label>Password</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="At least 8 characters" minLength={8} required />
          {authError && <div className="alert error">{authError}</div>}
          <button className="primary full" disabled={authBusy}>{authBusy ? "Please wait..." : authMode === "login" ? "Sign in" : "Create account"}</button>
          <p className="switch-auth">
            {authMode === "login" ? "New to BlindSpot AI?" : "Already have an account?"}
            <button type="button" className="link-button" onClick={() => { setAuthMode(authMode === "login" ? "register" : "login"); setAuthError(""); }}>
              {authMode === "login" ? "Create account" : "Sign in"}
            </button>
          </p>
          <div className={`connection ${backend}`}><i /> Backend {backend}</div>
        </form>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark small">B</div><div>BLINDSPOT<span>AI NEXUS</span></div></div>
        <div className="workspace-label">WORKSPACE</div>
        <nav>
          {navItems.map(([label, icon]) => (
            <button key={label} className={`nav-item ${page === label ? "active" : ""}`} onClick={() => setPage(label)}>
              <span className="nav-icon">{icon === "grid-2x2" ? "▦" : icon === "scan-search" ? "⌕" : icon === "history" ? "◷" : "✧"}</span>{label}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="connection"><i /> Backend {backend}</div>
          <div className="user-mini"><div className="avatar">{(user.email || "U")[0].toUpperCase()}</div><div className="user-email">{user.email}<small>Workspace account</small></div></div>
          <button className="logout" onClick={logout}>↪ Sign out</button>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div><div className="breadcrumb">Workspace <span>/</span> {page}</div><h2>{page}</h2></div>
          <div className="top-actions"><span className="date-label">{new Date().toLocaleDateString()}</span><button className="outline" onClick={loadProjects}>↻ Refresh</button></div>
        </header>

        {notice && <div className="alert notice">{notice}<button onClick={() => setNotice("")}>×</button></div>}

        {page === "Dashboard" && <>
          <section className="welcome-row">
            <div><p className="eyebrow">PROJECT INTELLIGENCE</p><h1>Your project overview</h1><p className="muted">Monitor your documents, reviews and identified risks in one place.</p></div>
            <button className="primary" onClick={() => document.getElementById("upload-area")?.scrollIntoView({ behavior: "smooth" })}>＋ New project</button>
          </section>
          <section className="stats-grid">
            <Stat label="Total projects" value={projects.length} note="Uploaded to workspace" icon="▣" />
            <Stat label="Analyzed projects" value={analyzedCount} note="AI review completed" icon="✓" />
            <Stat label="Pending review" value={pendingCount} note="Waiting for analysis" icon="◷" />
            <Stat label="Review coverage" value={projects.length ? `${Math.round(analyzedCount / projects.length * 100)}%` : "0%"} note="Analyzed / total projects" icon="◉" />
          </section>
          <section className="content-grid">
            <div className="panel upload-panel" id="upload-area">
              <div className="panel-heading"><div><p className="eyebrow">GET STARTED</p><h3>Upload a project document</h3></div><span className="soft-icon">↑</span></div>
              <p className="muted">Add a PDF, DOCX or TXT file. BlindSpot AI will index its text for analysis and evidence-based chat.</p>
              <form onSubmit={uploadProject}>
                <label className="field-label">Project name (optional)</label>
                <input value={projectName} onChange={(e) => setProjectName(e.target.value)} placeholder="e.g. Smart Irrigation System" />
                <label className="drop-zone">
                  <input type="file" accept=".pdf,.docx,.txt" onChange={(e) => setFile(e.target.files?.[0] || null)} />
                  <span className="upload-symbol">⇧</span><b>{file ? file.name : "Choose a document"}</b><small>PDF, DOCX or TXT · Maximum 20 MB</small>
                </label>
                <button className="primary full" disabled={uploadBusy || !file}>{uploadBusy ? "Uploading and indexing..." : "Upload project"}</button>
              </form>
            </div>
            <div className="panel quick-panel">
              <div className="panel-heading"><div><p className="eyebrow">WORKSPACE HEALTH</p><h3>Review activity</h3></div><span className="soft-icon">◈</span></div>
              <div className="activity-line"><span>Documents uploaded</span><b>{projects.length}</b></div>
              <div className="progress-track"><i style={{ width: `${projects.length ? analyzedCount / projects.length * 100 : 0}%` }} /></div>
              <div className="activity-line"><span>Analysis completed</span><b>{analyzedCount}</b></div>
              <div className="activity-line"><span>Awaiting analysis</span><b>{pendingCount}</b></div>
              <div className="tip-box"><b>Next step</b><p>Run AI analysis on an uploaded project to generate findings and recommendations.</p><button className="text-action" onClick={() => setPage("Project analysis")}>Go to project analysis →</button></div>
            </div>
          </section>
          <ProjectsTable projects={projects.slice(0, 5)} loading={loading} onAnalyze={analyzeProject} onView={viewReport} onChat={openChat} busyProject={busyProject} compact />
        </>}

        {page === "Project analysis" && <>
          <section className="welcome-row"><div><p className="eyebrow">DOCUMENT REVIEW</p><h1>Project analysis</h1><p className="muted">Run an AI review or open an existing report.</p></div></section>
          <ProjectsTable projects={projects} loading={loading} onAnalyze={analyzeProject} onView={viewReport} onChat={openChat} busyProject={busyProject} />
          {report && <section className="panel report-panel">
            <div className="report-title"><div><p className="eyebrow">AI REVIEW REPORT</p><h2>{selectedProject?.name || "Project report"}</h2></div><button className="outline" onClick={() => selectedProject && downloadPdf(selectedProject)}>↓ Export PDF</button></div>
            <p className="report-summary">{report.summary || report.overview || "Analysis completed. Review the findings and recommendations below."}</p>
            <div className="risk-grid">
              <RiskTile label="High severity" value={severityCount("high")} tone="high" />
              <RiskTile label="Medium severity" value={severityCount("medium")} tone="medium" />
              <RiskTile label="Low severity" value={severityCount("low")} tone="low" />
              <RiskTile label="Total findings" value={findings.length} tone="neutral" />
            </div>
            <h3>Risk overview</h3>
            {findings.length ? <div className="heatmap">{findings.map((f, i) => {
              const severity = String(f.severity || f.risk_level || "unclassified").toLowerCase();
              const tone = severity.includes("high") ? "high" : severity.includes("medium") ? "medium" : severity.includes("low") ? "low" : "neutral";
              return <div className={`heat-cell ${tone}`} key={i}><b>{f.title || f.issue || `Finding ${i + 1}`}</b><span>{f.severity || f.risk_level || "Severity not provided"}</span></div>;
            })}</div> : <p className="muted">No structured findings were returned in this report.</p>}
            <h3>Findings</h3>
            {findings.length ? findings.map((f, i) => <div className="finding" key={i}><div><b>{f.title || f.issue || `Finding ${i + 1}`}</b><span className={`severity ${String(f.severity || f.risk_level || "").toLowerCase()}`}>{f.severity || f.risk_level || "Unclassified"}</span></div><p>{f.description || f.details || f.explanation || "No additional description supplied."}</p>{f.recommendation && <small>Recommendation: {f.recommendation}</small>}</div>) : <p className="muted">Open a report with findings to view details.</p>}
            {Array.isArray(report.recommendations) && <><h3>Recommendations</h3><ul className="recommendations">{report.recommendations.map((r, i) => <li key={i}>{typeof r === "string" ? r : r.text || r.description || JSON.stringify(r)}</li>)}</ul></>}
            {report.disclaimer && <p className="disclaimer">{report.disclaimer}</p>}
          </section>}
        </>}

        {page === "History" && <>
          <section className="welcome-row"><div><p className="eyebrow">YOUR WORKSPACE RECORD</p><h1>Project history</h1><p className="muted">All projects uploaded to your account, ordered by latest upload.</p></div></section>
          <ProjectsTable projects={projects} loading={loading} onAnalyze={analyzeProject} onView={viewReport} onChat={openChat} busyProject={busyProject} />
          <section className="panel compare-panel">
            <div className="panel-heading"><div><p className="eyebrow">SIDE-BY-SIDE REVIEW</p><h3>Compare projects</h3></div><span className="muted">{compareIds.length} selected</span></div>
            <p className="muted">Select up to three projects to compare their available metadata and analysis status.</p>
            <div className="compare-select">{projects.map((p) => <label key={p.id}><input type="checkbox" checked={compareIds.includes(p.id)} disabled={!compareIds.includes(p.id) && compareIds.length >= 3} onChange={(e) => setCompareIds((old) => e.target.checked ? [...old, p.id] : old.filter((id) => id !== p.id))} />{p.name}</label>)}</div>
            {selectedProjects.length > 0 && <div className="compare-table-wrap"><table className="compare-table"><thead><tr><th>Metric</th>{selectedProjects.map((p) => <th key={p.id}>{p.name}</th>)}</tr></thead><tbody><tr><td>File</td>{selectedProjects.map((p) => <td key={p.id}>{p.filename}</td>)}</tr><tr><td>Status</td>{selectedProjects.map((p) => <td key={p.id}>{p.status}</td>)}</tr><tr><td>Uploaded</td>{selectedProjects.map((p) => <td key={p.id}>{p.created_at ? new Date(p.created_at).toLocaleDateString() : "—"}</td>)}</tr></tbody></table></div>}
          </section>
        </>}

        {page === "AI Chat Assistant" && <>
          <section className="welcome-row"><div><p className="eyebrow">ASK YOUR DOCUMENTS</p><h1>AI Chat Assistant</h1><p className="muted">Ask questions grounded in the selected project's indexed content.</p></div></section>
          <section className="chat-layout">
            <div className="panel chat-projects"><h3>Select a project</h3>{projects.map((p) => <button key={p.id} className={`chat-project ${chatProject?.id === p.id ? "selected" : ""}`} onClick={() => openChat(p)}><span className="file-icon">▤</span><span>{p.name}<small>{p.filename}</small></span></button>)}</div>
            <div className="panel chat-window">
              <div className="chat-head"><div><b>{chatProject?.name || "Choose a project"}</b><small>{chatProject ? "Project-grounded assistant" : "Select a project to begin"}</small></div><span className="ai-pill">✧ AI ASSISTANT</span></div>
              <div className="chat-body">
                {!chatProject && <div className="empty-state"><span>✧</span><h3>Start a project conversation</h3><p>Choose a project from the left to ask questions about its document.</p></div>}
                {chatProject && chatMessages.length === 0 && <div className="empty-state"><span>✧</span><h3>What would you like to know?</h3><p>Ask about the project scope, risks, requirements or details found in the uploaded document.</p></div>}
                {chatMessages.map((m, i) => <div className={`message ${m.role === "user" ? "mine" : ""}`} key={i}><div className="message-role">{m.role === "user" ? "YOU" : "BLINDSPOT AI"}</div><div className="message-bubble">{m.message}</div>{m.sources?.length > 0 && <small className="sources">Sources: {m.sources.map((s) => `${s.filename} (chunk ${s.chunk})`).join(", ")}</small>}</div>)}
                {chatBusy && <div className="typing">BlindSpot AI is thinking…</div>}
                {chatError && <div className="alert error">{chatError}</div>}
              </div>
              <form className="chat-compose" onSubmit={sendChat}><input value={chatInput} onChange={(e) => setChatInput(e.target.value)} placeholder={chatProject ? "Ask a question about this project..." : "Select a project first"} disabled={!chatProject || chatBusy} /><button className="primary" disabled={!chatProject || !chatInput.trim() || chatBusy}>Send ↑</button></form>
            </div>
          </section>
        </>}

        <footer>BLINDSPOT AI NEXUS <span>•</span> Intelligent Project Review</footer>
      </main>
    </div>
  );
}

function Stat({ label, value, note, icon }) {
  return <div className="stat-card"><div className="stat-top"><span>{label}</span><i>{icon}</i></div><strong>{value}</strong><small>{note}</small></div>;
}
function RiskTile({ label, value, tone }) {
  return <div className={`risk-tile ${tone}`}><span>{label}</span><b>{value}</b></div>;
}
function ProjectsTable({ projects, loading, onAnalyze, onView, onChat, busyProject, compact = false }) {
  return <section className="panel projects-panel">
    <div className="panel-heading"><div><p className="eyebrow">{compact ? "RECENT ACTIVITY" : "PROJECT LIBRARY"}</p><h3>{compact ? "Recent projects" : "All projects"}</h3></div><span className="muted">{projects.length} projects</span></div>
    {loading ? <p className="muted">Loading projects...</p> : projects.length === 0 ? <div className="empty-row"><span>▤</span><b>No projects uploaded yet</b><small>Upload your first project document from the dashboard.</small></div> :
      <div className="table-wrap"><table><thead><tr><th>Project</th><th>File</th><th>Uploaded</th><th>Status</th><th>Actions</th></tr></thead><tbody>
        {projects.map((p) => <tr key={p.id}><td><b>{p.name}</b></td><td>{p.filename}</td><td>{p.created_at ? new Date(p.created_at).toLocaleDateString() : "—"}</td><td><span className={`status ${p.status === "Analyzed" ? "done" : ""}`}>{p.status || "Uploaded"}</span></td><td><div className="table-actions"><button onClick={() => onAnalyze(p)} disabled={busyProject === p.id}>{busyProject === p.id ? "Working..." : "Analyze"}</button><button onClick={() => onView(p)}>Report</button><button onClick={() => onChat(p)}>Chat</button></div></td></tr>)}
      </tbody></table></div>}
  </section>;
}

export default App;
