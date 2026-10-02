"use client";

import { useState, useEffect, useCallback } from "react";
import { useAuthStore, useAppStore } from "@/lib/store";
import { api, Case, Investigation, InvestigationDetail, GraphData } from "@/lib/api";
import styles from "./dashboard.module.css";

export default function DashboardPage() {
  const { user, isLoading: authLoading, loadFromStorage, logout } = useAuthStore();
  const { cases, isLoadingCases, loadCases, investigations, loadInvestigations } = useAppStore();
  const [view, setView] = useState<"cases" | "case-detail" | "investigation">("cases");
  const [selectedCase, setSelectedCase] = useState<Case | null>(null);
  const [selectedInvestigation, setSelectedInvestigation] = useState<InvestigationDetail | null>(null);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [showCreateCase, setShowCreateCase] = useState(false);
  const [showCreateInv, setShowCreateInv] = useState(false);

  useEffect(() => {
    loadFromStorage();
  }, [loadFromStorage]);

  useEffect(() => {
    if (user) loadCases();
  }, [user, loadCases]);

  const openCase = useCallback(async (c: Case) => {
    setSelectedCase(c);
    await loadInvestigations(c.id);
    setView("case-detail");
  }, [loadInvestigations]);

  const openInvestigation = useCallback(async (inv: Investigation) => {
    try {
      const detail = await api.getInvestigation(inv.id);
      setSelectedInvestigation(detail);
      const graph = await api.getInvestigationGraph(inv.id);
      setGraphData(graph);
      setView("investigation");
    } catch { /* handle error */ }
  }, []);

  if (authLoading) {
    return (
      <div className={styles.loadingContainer}>
        <div className="spinner" />
        <p>Loading ZAPRICA...</p>
      </div>
    );
  }

  if (!user) {
    if (typeof window !== "undefined") window.location.href = "/";
    return null;
  }

  return (
    <div className={styles.dashLayout}>
      {/* ── Sidebar ── */}
      <aside className={styles.sidebar}>
        <div className={styles.sidebarLogo}>
          <h2 className={styles.brandText}>ZAPRICA</h2>
          <span className={styles.versionBadge}>v0.1 MVP</span>
        </div>

        <nav className={styles.sidebarNav}>
          <button
            className={`${styles.navItem} ${view === "cases" ? styles.navItemActive : ""}`}
            onClick={() => setView("cases")}
          >
            <span className={styles.navIcon}>📁</span>
            Cases
          </button>
          {selectedCase && (
            <button
              className={`${styles.navItem} ${styles.navItemSub} ${view === "case-detail" ? styles.navItemActive : ""}`}
              onClick={() => setView("case-detail")}
            >
              <span className={styles.navIcon}>📋</span>
              {selectedCase.title.substring(0, 20)}
            </button>
          )}
          {selectedInvestigation && (
            <button
              className={`${styles.navItem} ${styles.navItemSub} ${view === "investigation" ? styles.navItemActive : ""}`}
              onClick={() => setView("investigation")}
            >
              <span className={styles.navIcon}>🔍</span>
              Investigation
            </button>
          )}
        </nav>

        <div className={styles.sidebarFooter}>
          <div className={styles.userInfo}>
            <div className={styles.userAvatar}>
              {user.full_name.charAt(0).toUpperCase()}
            </div>
            <div>
              <div className={styles.userName}>{user.full_name}</div>
              <div className={styles.userRole}>{user.role}</div>
            </div>
          </div>
          <button className="btn btn-ghost btn-sm" onClick={logout}>
            Logout
          </button>
        </div>
      </aside>

      {/* ── Main Content ── */}
      <main className={styles.mainContent}>
        {view === "cases" && (
          <CasesView
            cases={cases}
            isLoading={isLoadingCases}
            onOpenCase={openCase}
            onCreateCase={() => setShowCreateCase(true)}
          />
        )}

        {view === "case-detail" && selectedCase && (
          <CaseDetailView
            caseData={selectedCase}
            investigations={investigations}
            onOpenInvestigation={openInvestigation}
            onCreateInvestigation={() => setShowCreateInv(true)}
            onBack={() => setView("cases")}
          />
        )}

        {view === "investigation" && selectedInvestigation && (
          <InvestigationView
            investigation={selectedInvestigation}
            graphData={graphData}
            onBack={() => setView("case-detail")}
          />
        )}
      </main>

      {/* ── Modals ── */}
      {showCreateCase && (
        <CreateCaseModal
          onClose={() => setShowCreateCase(false)}
          onCreated={(c) => {
            useAppStore.getState().addCase(c);
            setShowCreateCase(false);
          }}
        />
      )}

      {showCreateInv && selectedCase && (
        <CreateInvestigationModal
          caseId={selectedCase.id}
          onClose={() => setShowCreateInv(false)}
          onCreated={(inv) => {
            useAppStore.getState().addInvestigation(inv);
            setShowCreateInv(false);
          }}
        />
      )}
    </div>
  );
}

/* ── Cases View ────────────────────────────────────────────── */

function CasesView({
  cases,
  isLoading,
  onOpenCase,
  onCreateCase,
}: {
  cases: Case[];
  isLoading: boolean;
  onOpenCase: (c: Case) => void;
  onCreateCase: () => void;
}) {
  return (
    <div className={styles.pageContent}>
      <div className={styles.pageHeader}>
        <div>
          <h1>Investigation Cases</h1>
          <p className={styles.pageSubtitle}>
            Manage and track your OSINT investigation cases
          </p>
        </div>
        <button className="btn btn-primary" onClick={onCreateCase}>
          + New Case
        </button>
      </div>

      {/* Stats Cards */}
      <div className={`grid grid-4 ${styles.statsGrid}`}>
        <StatCard label="Total Cases" value={cases.length} icon="📁" />
        <StatCard label="Active" value={cases.filter((c) => c.status === "in_progress").length} icon="⚡" color="info" />
        <StatCard label="Open" value={cases.filter((c) => c.status === "open").length} icon="📂" color="success" />
        <StatCard label="Closed" value={cases.filter((c) => c.status === "closed").length} icon="✅" color="neutral" />
      </div>

      {isLoading ? (
        <div className={styles.emptyState}>
          <div className="spinner" />
          <p>Loading cases...</p>
        </div>
      ) : cases.length === 0 ? (
        <div className={styles.emptyState}>
          <span className={styles.emptyIcon}>📁</span>
          <h3>No Cases Yet</h3>
          <p>Create your first investigation case to get started</p>
          <button className="btn btn-primary" onClick={onCreateCase}>
            + Create Case
          </button>
        </div>
      ) : (
        <div className={styles.caseGrid}>
          {cases.map((c) => (
            <div key={c.id} className={`card ${styles.caseCard}`} onClick={() => onOpenCase(c)}>
              <div className={styles.caseCardHeader}>
                <StatusBadge status={c.status} />
                <span className={styles.caseDate}>
                  {new Date(c.created_at).toLocaleDateString()}
                </span>
              </div>
              <h3 className={styles.caseTitle}>{c.title}</h3>
              {c.description && (
                <p className={styles.caseDesc}>{c.description}</p>
              )}
              <div className={styles.caseFooter}>
                <span className={styles.caseMeta}>
                  {c.investigation_count} investigation{c.investigation_count !== 1 ? "s" : ""}
                </span>
                {c.tags.length > 0 && (
                  <div className={styles.caseTags}>
                    {c.tags.slice(0, 3).map((t) => (
                      <span key={t} className={styles.caseTag}>{t}</span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Case Detail View ──────────────────────────────────────── */

function CaseDetailView({
  caseData,
  investigations,
  onOpenInvestigation,
  onCreateInvestigation,
  onBack,
}: {
  caseData: Case;
  investigations: Investigation[];
  onOpenInvestigation: (inv: Investigation) => void;
  onCreateInvestigation: () => void;
  onBack: () => void;
}) {
  return (
    <div className={styles.pageContent}>
      <div className={styles.pageHeader}>
        <div>
          <button className="btn btn-ghost btn-sm" onClick={onBack}>
            ← Back to Cases
          </button>
          <h1 style={{ marginTop: "8px" }}>{caseData.title}</h1>
          {caseData.description && (
            <p className={styles.pageSubtitle}>{caseData.description}</p>
          )}
        </div>
        <div className="flex gap-sm">
          <StatusBadge status={caseData.status} />
          <button className="btn btn-primary" onClick={onCreateInvestigation}>
            + New Investigation
          </button>
        </div>
      </div>

      {investigations.length === 0 ? (
        <div className={styles.emptyState}>
          <span className={styles.emptyIcon}>🔍</span>
          <h3>No Investigations</h3>
          <p>Start an autonomous investigation by providing a seed (domain, IP, email, etc.)</p>
          <button className="btn btn-primary" onClick={onCreateInvestigation}>
            + Launch Investigation
          </button>
        </div>
      ) : (
        <div className={styles.invList}>
          {investigations.map((inv) => (
            <div
              key={inv.id}
              className={`card ${styles.invCard}`}
              onClick={() => onOpenInvestigation(inv)}
            >
              <div className={styles.invCardHeader}>
                <div className="flex items-center gap-sm">
                  <InvestigationStatusDot status={inv.status} />
                  <span className={styles.invSeedType}>{inv.seed_type.toUpperCase()}</span>
                </div>
                <StatusBadge status={inv.status} />
              </div>

              <div className={styles.invSeedValue}>
                <code>{inv.seed_value}</code>
              </div>

              <div className={styles.invStats}>
                <InvStat label="Entities" value={inv.entity_count} />
                <InvStat label="Iterations" value={inv.iteration_count} />
                <InvStat label="Tool Calls" value={inv.tool_call_count} />
                <InvStat label="Step" value={inv.current_step || "—"} />
              </div>

              {inv.findings_summary && (
                <p className={styles.invSummary}>{inv.findings_summary}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Investigation Detail View ─────────────────────────────── */

function InvestigationView({
  investigation,
  graphData,
  onBack,
}: {
  investigation: InvestigationDetail;
  graphData: GraphData | null;
  onBack: () => void;
}) {
  const [tab, setTab] = useState<"graph" | "steps" | "entities">("graph");

  return (
    <div className={styles.pageContent}>
      <div className={styles.pageHeader}>
        <div>
          <button className="btn btn-ghost btn-sm" onClick={onBack}>
            ← Back to Case
          </button>
          <h1 style={{ marginTop: "8px" }}>
            Investigation: <code className={styles.seedCode}>{investigation.seed_value}</code>
          </h1>
          <p className={styles.pageSubtitle}>
            Seed Type: {investigation.seed_type} · Status: {investigation.status}
          </p>
        </div>
        <StatusBadge status={investigation.status} />
      </div>

      {/* Stats Row */}
      <div className={`grid grid-4 ${styles.statsGrid}`}>
        <StatCard label="Entities Found" value={investigation.entity_count} icon="🔗" color="info" />
        <StatCard label="Tool Calls" value={investigation.tool_call_count} icon="🛠️" color="success" />
        <StatCard label="Iterations" value={investigation.iteration_count} icon="🔄" />
        <StatCard label="Steps" value={investigation.steps.length} icon="📝" color="neutral" />
      </div>

      {/* Tab Navigation */}
      <div className={styles.tabBar}>
        <button className={`${styles.tabBtn} ${tab === "graph" ? styles.tabBtnActive : ""}`} onClick={() => setTab("graph")}>
          🕸️ Knowledge Graph
        </button>
        <button className={`${styles.tabBtn} ${tab === "steps" ? styles.tabBtnActive : ""}`} onClick={() => setTab("steps")}>
          📋 Investigation Steps
        </button>
        <button className={`${styles.tabBtn} ${tab === "entities" ? styles.tabBtnActive : ""}`} onClick={() => setTab("entities")}>
          🔗 Entities
        </button>
      </div>

      {/* Tab Content */}
      {tab === "graph" && <GraphView graphData={graphData} />}
      {tab === "steps" && <StepsView steps={investigation.steps} />}
      {tab === "entities" && <EntitiesView graphData={graphData} />}

      {/* Summary */}
      {investigation.findings_summary && (
        <div className={`card ${styles.summaryCard}`}>
          <h3>📄 Findings Summary</h3>
          <p>{investigation.findings_summary}</p>
        </div>
      )}
    </div>
  );
}

/* ── Graph Visualization (Placeholder — SSR-safe) ──────────── */

function GraphView({ graphData }: { graphData: GraphData | null }) {
  if (!graphData || (graphData.nodes.length === 0 && graphData.edges.length === 0)) {
    return (
      <div className={styles.emptyState}>
        <span className={styles.emptyIcon}>🕸️</span>
        <h3>No Graph Data</h3>
        <p>Entities and relationships will appear here once the investigation discovers them.</p>
      </div>
    );
  }

  const entityColors: Record<string, string> = {
    Domain: "#00d4ff",
    IP: "#7c3aed",
    Email: "#ec4899",
    Organization: "#10b981",
    Person: "#f59e0b",
    FileHash: "#ef4444",
  };

  return (
    <div className={`card ${styles.graphContainer}`}>
      <div className={styles.graphLegend}>
        {Object.entries(entityColors).map(([type, color]) => (
          <span key={type} className={styles.legendItem}>
            <span className={styles.legendDot} style={{ background: color }} />
            {type}
          </span>
        ))}
      </div>
      <div className={styles.graphCanvas}>
        {/* Node-link visualization using CSS */}
        <div className={styles.graphNodes}>
          {graphData.nodes.map((node, i) => (
            <div
              key={`${node.entity_type}-${node.value}-${i}`}
              className={styles.graphNode}
              style={{
                borderColor: entityColors[node.entity_type] || "#64748b",
                left: `${15 + (i % 5) * 18}%`,
                top: `${15 + Math.floor(i / 5) * 22}%`,
              }}
              title={`${node.entity_type}: ${node.value}`}
            >
              <span className={styles.graphNodeType} style={{ color: entityColors[node.entity_type] || "#64748b" }}>
                {node.entity_type}
              </span>
              <span className={styles.graphNodeValue}>{node.value}</span>
            </div>
          ))}
        </div>
        {graphData.edges.length > 0 && (
          <div className={styles.graphEdgeInfo}>
            <p>{graphData.edges.length} relationship{graphData.edges.length !== 1 ? "s" : ""} discovered</p>
            {graphData.edges.slice(0, 8).map((edge, i) => (
              <div key={i} className={styles.edgeLine}>
                <code>{edge.source_value}</code>
                <span className={styles.edgeArrow}>→ {edge.relationship} →</span>
                <code>{edge.target_value}</code>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Steps View ────────────────────────────────────────────── */

function StepsView({ steps }: { steps: InvestigationDetail["steps"] }) {
  if (steps.length === 0) {
    return (
      <div className={styles.emptyState}>
        <span className={styles.emptyIcon}>📋</span>
        <h3>No Steps Yet</h3>
        <p>Investigation steps will appear here as the agent executes.</p>
      </div>
    );
  }

  return (
    <div className={styles.stepsList}>
      {steps.map((step) => (
        <div key={step.id} className={`card ${styles.stepCard}`}>
          <div className={styles.stepHeader}>
            <span className={styles.stepNum}>#{step.step_number}</span>
            <span className={styles.stepType}>{step.step_type}</span>
            <StatusBadge status={step.status} />
          </div>
          {step.tool_name && (
            <div className={styles.stepTool}>
              <code>🛠️ {step.tool_name}</code>
              {step.tool_input && (
                <pre className={styles.stepJson}>
                  {JSON.stringify(step.tool_input, null, 2)}
                </pre>
              )}
            </div>
          )}
          {step.entities_extracted.length > 0 && (
            <div className={styles.stepEntities}>
              {step.entities_extracted.length} entities extracted
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

/* ── Entities View ─────────────────────────────────────────── */

function EntitiesView({ graphData }: { graphData: GraphData | null }) {
  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className={styles.emptyState}>
        <span className={styles.emptyIcon}>🔗</span>
        <h3>No Entities</h3>
        <p>Discovered entities will be listed here.</p>
      </div>
    );
  }

  return (
    <div className={styles.entitiesGrid}>
      {graphData.nodes.map((node, i) => (
        <div key={i} className={`card ${styles.entityCard}`}>
          <span className={styles.entityType}>{node.entity_type}</span>
          <code className={styles.entityValue}>{node.value}</code>
          {Object.keys(node.properties).length > 0 && (
            <div className={styles.entityProps}>
              {Object.entries(node.properties).map(([k, v]) => (
                <div key={k} className={styles.entityProp}>
                  <span className={styles.propKey}>{k}:</span>
                  <span className={styles.propVal}>{String(v)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

/* ── Create Case Modal ─────────────────────────────────────── */

function CreateCaseModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (c: Case) => void;
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [attestation, setAttestation] = useState(false);
  const [tags, setTags] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!attestation) {
      setError("Authorization attestation is required per DPDP Act compliance.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const newCase = await api.createCase({
        title,
        description: description || undefined,
        authorization_attestation: attestation,
        tags: tags ? tags.split(",").map((t) => t.trim()) : [],
      });
      onCreated(newCase);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create case");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={`card ${styles.modal}`} onClick={(e) => e.stopPropagation()}>
        <h2>Create Investigation Case</h2>
        <form onSubmit={handleSubmit} className={styles.modalForm}>
          <div className={styles.formGroup}>
            <label className="label" htmlFor="case-title">Case Title</label>
            <input id="case-title" className="input" value={title} onChange={(e) => setTitle(e.target.value)} required placeholder="e.g., APT-29 Infrastructure Investigation" />
          </div>
          <div className={styles.formGroup}>
            <label className="label" htmlFor="case-desc">Description</label>
            <textarea id="case-desc" className="input textarea" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Brief description of the investigation scope..." rows={3} />
          </div>
          <div className={styles.formGroup}>
            <label className="label" htmlFor="case-tags">Tags (comma-separated)</label>
            <input id="case-tags" className="input" value={tags} onChange={(e) => setTags(e.target.value)} placeholder="apt, infrastructure, recon" />
          </div>
          <div className={styles.attestation}>
            <input
              type="checkbox"
              id="attestation"
              checked={attestation}
              onChange={(e) => setAttestation(e.target.checked)}
            />
            <label htmlFor="attestation" className={styles.attestationLabel}>
              I confirm this investigation is <strong>authorized</strong> and complies with the Digital Personal Data Protection (DPDP) Act, 2023.
            </label>
          </div>
          {error && <div className={styles.errorMsg}>{error}</div>}
          <div className="flex gap-sm" style={{ justifyContent: "flex-end" }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? <span className="spinner" /> : "Create Case"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ── Create Investigation Modal ────────────────────────────── */

function CreateInvestigationModal({
  caseId,
  onClose,
  onCreated,
}: {
  caseId: string;
  onClose: () => void;
  onCreated: (inv: Investigation) => void;
}) {
  const [seedType, setSeedType] = useState("domain");
  const [seedValue, setSeedValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const seedTypes = [
    { value: "domain", label: "Domain", placeholder: "example.com" },
    { value: "ip", label: "IP Address", placeholder: "93.184.216.34" },
    { value: "email", label: "Email", placeholder: "admin@example.com" },
    { value: "hash", label: "File Hash", placeholder: "SHA256 hash" },
    { value: "person", label: "Person", placeholder: "John Doe" },
    { value: "organization", label: "Organization", placeholder: "Acme Corp" },
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const inv = await api.createInvestigation(caseId, {
        seed_type: seedType,
        seed_value: seedValue,
      });
      onCreated(inv);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create investigation");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={`card ${styles.modal}`} onClick={(e) => e.stopPropagation()}>
        <h2>Launch Investigation</h2>
        <p className={styles.modalSubtext}>
          The autonomous agent will investigate this seed using available OSINT tools.
        </p>
        <form onSubmit={handleSubmit} className={styles.modalForm}>
          <div className={styles.formGroup}>
            <label className="label">Seed Type</label>
            <div className={styles.seedTypeGrid}>
              {seedTypes.map((st) => (
                <button
                  key={st.value}
                  type="button"
                  className={`${styles.seedTypeBtn} ${seedType === st.value ? styles.seedTypeBtnActive : ""}`}
                  onClick={() => setSeedType(st.value)}
                >
                  {st.label}
                </button>
              ))}
            </div>
          </div>
          <div className={styles.formGroup}>
            <label className="label" htmlFor="seed-value">Seed Value</label>
            <input
              id="seed-value"
              className="input"
              value={seedValue}
              onChange={(e) => setSeedValue(e.target.value)}
              required
              placeholder={seedTypes.find((s) => s.value === seedType)?.placeholder}
            />
          </div>
          {error && <div className={styles.errorMsg}>{error}</div>}
          <div className="flex gap-sm" style={{ justifyContent: "flex-end" }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? <span className="spinner" /> : "🚀 Launch Investigation"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ── Helper Components ─────────────────────────────────────── */

function StatCard({
  label,
  value,
  icon,
  color,
}: {
  label: string;
  value: number | string;
  icon: string;
  color?: string;
}) {
  return (
    <div className={`card ${styles.statCard}`}>
      <span className={styles.statIcon}>{icon}</span>
      <div className={styles.statValue} data-color={color}>{value}</div>
      <div className={styles.statLabel}>{label}</div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colorMap: Record<string, string> = {
    open: "info",
    in_progress: "warning",
    closed: "neutral",
    archived: "neutral",
    pending: "neutral",
    planning: "info",
    executing: "warning",
    extracting: "warning",
    graphing: "info",
    evaluating: "info",
    pivoting: "info",
    completed: "success",
    failed: "danger",
    cancelled: "neutral",
    paused_hitl: "warning",
  };
  const badgeColor = colorMap[status] || "neutral";
  return <span className={`badge badge-${badgeColor}`}>{status.replace(/_/g, " ")}</span>;
}

function InvestigationStatusDot({ status }: { status: string }) {
  const classMap: Record<string, string> = {
    pending: "",
    planning: "running",
    executing: "running",
    extracting: "running",
    graphing: "running",
    evaluating: "running",
    pivoting: "running",
    completed: "active",
    failed: "error",
    cancelled: "",
    paused_hitl: "paused",
  };
  return <span className={`pulse-dot ${classMap[status] || ""}`} />;
}

function InvStat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className={styles.invStat}>
      <span className={styles.invStatValue}>{value}</span>
      <span className={styles.invStatLabel}>{label}</span>
    </div>
  );
}

// Types for the investigation create form
interface InvestigationCreateInput {
  seed_type: string;
  seed_value: string;
  max_iterations?: number;
  max_tool_calls?: number;
  max_time_seconds?: number;
}
