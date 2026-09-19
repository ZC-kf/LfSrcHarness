import {
  Activity,
  AlertOctagon,
  Archive,
  Bot,
  Boxes,
  CheckCircle2,
  ChevronRight,
  CircleDot,
  ClipboardCheck,
  Clock3,
  FileSearch,
  Fingerprint,
  Gauge,
  ListChecks,
  MonitorCog,
  Radio,
  RefreshCw,
  ScrollText,
  ServerCog,
  Settings,
  ShieldCheck,
  TerminalSquare,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

declare global {
  interface Window { pywebview?: { api: { get_token: () => Promise<string> } } }
}

type Page = "dashboard" | "tasks" | "runs" | "events" | "evidence" | "reports" | "approvals" | "providers" | "nodes" | "settings";

type ProviderKind = "openai_compatible" | "anthropic" | "gemini" | "ollama";
type ProviderRecord = { name: string; kind: ProviderKind; base_url: string; model: string; has_api_key: boolean };
type ScopeRecord = {
  name: string; targets: string[]; time_windows: Array<{ start: string; end: string }>;
  rate_limit: { requests: number; per_seconds: number }; prohibited_actions: string[];
  privileges: { allow_privileged_container?: boolean; allow_host_network?: boolean; allow_docker_socket?: boolean };
};

type TaskRecord = {
  id: string;
  status: "queued" | "running" | "pending_approval" | "succeeded" | "failed" | "stopped";
  active_plugin: string;
  attempts: number;
  spec: { target: string; objective: string; priority: number; node: string };
  updated_at: string;
};

type Approval = { id: string; status: string; actor?: string | null };

const navigation: Array<{ id: Page; label: string; icon: LucideIcon }> = [
  { id: "dashboard", label: "总览", icon: Gauge },
  { id: "tasks", label: "任务", icon: ListChecks },
  { id: "runs", label: "运行", icon: Activity },
  { id: "events", label: "事件", icon: Radio },
  { id: "evidence", label: "证据", icon: Fingerprint },
  { id: "reports", label: "报告", icon: ScrollText },
  { id: "approvals", label: "审批", icon: ClipboardCheck },
  { id: "providers", label: "模型", icon: Bot },
  { id: "nodes", label: "节点", icon: ServerCog },
  { id: "settings", label: "设置", icon: Settings },
];

const statusLabel: Record<TaskRecord["status"], string> = {
  queued: "排队中",
  running: "运行中",
  pending_approval: "待审批",
  succeeded: "已完成",
  failed: "失败",
  stopped: "已停止",
};

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const token = window.pywebview?.api
    ? await window.pywebview.api.get_token()
    : localStorage.getItem("lfsrc-token") || "";
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export default function App() {
  const [page, setPage] = useState<Page>("dashboard");
  const [tasks, setTasks] = useState<TaskRecord[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [error, setError] = useState<string>("");
  const [refreshedAt, setRefreshedAt] = useState<Date>(new Date());

  const refresh = async () => {
    try {
      const [taskData, approvalData] = await Promise.all([
        api<TaskRecord[]>("/api/tasks"),
        api<Approval[]>("/api/approvals"),
      ]);
      setTasks(Array.isArray(taskData) ? taskData : []);
      setApprovals(Array.isArray(approvalData) ? approvalData : []);
      setError("");
      setRefreshedAt(new Date());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "API unavailable");
    }
  };

  useEffect(() => {
    void refresh();
    const ready = () => void refresh();
    window.addEventListener("pywebviewready", ready);
    const timer = window.setInterval(() => void refresh(), 5000);
    return () => { window.clearInterval(timer); window.removeEventListener("pywebviewready", ready); };
  }, []);

  const summary = useMemo(() => ({
    running: tasks.filter((task) => task.status === "running").length,
    queued: tasks.filter((task) => task.status === "queued").length,
    waiting: tasks.filter((task) => task.status === "pending_approval").length + approvals.filter((item) => item.status === "pending").length,
    completed: tasks.filter((task) => task.status === "succeeded").length,
  }), [tasks, approvals]);

  const emergencyStop = async () => {
    await api<void>("/api/emergency-stop", {
      method: "POST",
      body: JSON.stringify({ level: "global", action: "stop" }),
    });
    await refresh();
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark"><TerminalSquare size={22} /></div>
          <div><strong>LfSrcHarness</strong><span>OPERATOR CONSOLE</span></div>
        </div>
        <nav>
          {navigation.map(({ id, label, icon: Icon }) => (
            <button className={page === id ? "active" : ""} key={id} onClick={() => setPage(id)}>
              <Icon size={17} /><span>{label}</span>{page === id && <ChevronRight size={14} />}
            </button>
          ))}
        </nav>
        <div className="node-card">
          <div><span className="live-dot" /> local-node</div>
          <small>Python 3.12 · policy active</small>
        </div>
      </aside>

      <main>
        <header className="topbar">
          <div>
            <p className="eyebrow">AUTHORIZED AUTOMATION</p>
            <h1>{navigation.find((item) => item.id === page)?.label}</h1>
          </div>
          <div className="toolbar">
            <span className={error ? "connection bad" : "connection"}><CircleDot size={14} />{error ? "API 离线" : "实时连接"}</span>
            <button className="icon-button" onClick={() => void refresh()} aria-label="刷新"><RefreshCw size={17} /></button>
            <button className="danger-button" onClick={() => void emergencyStop()}><AlertOctagon size={16} />全局急停</button>
          </div>
        </header>

        <section className="content">
          {error && <div className="notice">未能读取 API：{error}。配置 Token 后重试。</div>}
          {page === "dashboard" && <Dashboard tasks={tasks} summary={summary} refreshedAt={refreshedAt} />}
          {page === "tasks" && <TaskTable tasks={tasks} title="任务队列" />}
          {page === "runs" && <TaskTable tasks={tasks.filter((task) => task.status !== "queued")} title="运行记录" />}
          {page === "events" && <EmptyPanel icon={Radio} title="实时事件流" text="选择运行后，通过 SSE 回放 JSONL 审计事件。" />}
          {page === "evidence" && <EmptyPanel icon={Fingerprint} title="证据仓库" text="内容寻址证据、哈希、来源与报告引用在这里统一检索。" />}
          {page === "reports" && <EmptyPanel icon={Archive} title="报告中心" text="Markdown、JSON、HTML、PDF 与 SARIF 归档入口。" />}
          {page === "approvals" && <ApprovalPanel approvals={approvals} />}
          {page === "providers" && <ProviderPanel />}
          {page === "nodes" && <NodePanel />}
          {page === "settings" && <SettingsPanel onSaved={() => void refresh()} />}
        </section>
      </main>
    </div>
  );
}

function Dashboard({ tasks, summary, refreshedAt }: { tasks: TaskRecord[]; summary: Record<string, number>; refreshedAt: Date }) {
  const metrics = [
    ["运行中", summary.running, Activity, "green"],
    ["排队", summary.queued, Clock3, "cyan"],
    ["待审批", summary.waiting, ShieldCheck, "amber"],
    ["已完成", summary.completed, CheckCircle2, "blue"],
  ] as const;
  return <>
    <div className="metrics">
      {metrics.map(([label, value, Icon, color]) => <article className={`metric ${color}`} key={label}>
        <div><span>{label}</span><strong>{value}</strong></div><Icon size={22} />
      </article>)}
    </div>
    <div className="dashboard-grid">
      <TaskTable tasks={tasks.slice(0, 6)} title="最近任务" />
      <section className="panel stack-panel">
        <div className="panel-title"><div><Boxes size={17} /><h2>执行栈</h2></div><small>{refreshedAt.toLocaleTimeString("zh-CN")}</small></div>
        {["Scope 校验", "Policy 决策", "Orchestrator 调度", "Runner 执行", "JSONL 审计", "Reporter 输出"].map((item, index) =>
          <div className="stack-row" key={item}><span>{String(index + 1).padStart(2, "0")}</span><p>{item}</p><i className={index < 3 ? "ready" : "idle"}>{index < 3 ? "READY" : "IDLE"}</i></div>)}
      </section>
    </div>
  </>;
}

function TaskTable({ tasks, title }: { tasks: TaskRecord[]; title: string }) {
  return <section className="panel task-panel">
    <div className="panel-title"><div><FileSearch size={17} /><h2>{title}</h2></div><span>{tasks.length} items</span></div>
    <div className="table-wrap"><table><thead><tr><th>任务</th><th>目标</th><th>插件</th><th>尝试</th><th>状态</th></tr></thead>
      <tbody>{tasks.length ? tasks.map((task) => <tr key={task.id}>
        <td><strong>{task.spec.objective}</strong><small>{task.id.slice(0, 18)}</small></td>
        <td>{task.spec.target}</td><td>{task.active_plugin}</td><td>{task.attempts}</td>
        <td><span className={`status-pill ${task.status}`}>{statusLabel[task.status]}</span></td>
      </tr>) : <tr><td className="empty-cell" colSpan={5}>暂无任务，等待 API 提交。</td></tr>}</tbody>
    </table></div>
  </section>;
}

function ApprovalPanel({ approvals }: { approvals: Approval[] }) {
  return <section className="panel wide-panel"><div className="panel-title"><div><ClipboardCheck size={17} /><h2>审批队列</h2></div></div>
    {approvals.length ? approvals.map((approval) => <div className="approval-row" key={approval.id}><code>{approval.id}</code><span className={`status-pill ${approval.status}`}>{approval.status}</span></div>) : <div className="empty-state">当前没有待处理审批。</div>}
  </section>;
}

function ProviderPanel() {
  const [items, setItems] = useState<ProviderRecord[]>([]);
  const [name, setName] = useState("");
  const [kind, setKind] = useState<ProviderKind>("openai_compatible");
  const [baseUrl, setBaseUrl] = useState("");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [feedback, setFeedback] = useState("");
  const [selected, setSelected] = useState("");
  const [message, setMessage] = useState("");
  const [reply, setReply] = useState("");
  const [sending, setSending] = useState(false);

  const load = async () => {
    const next = await api<ProviderRecord[]>("/api/settings/providers");
    setItems(next);
    setSelected((current) => next.some((item) => item.name === current) ? current : next[0]?.name || "");
  };
  useEffect(() => { void load().catch((reason) => setFeedback(String(reason))); }, []);

  const send = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selected || !message.trim()) return;
    setSending(true);
    setReply("");
    try {
      const result = await api<{ text: string }>(`/api/models/${encodeURIComponent(selected)}/generate`, {
        method: "POST", body: JSON.stringify({ messages: [{ role: "user", content: message }] }),
      });
      setReply(result.text);
    } catch (reason) { setReply(`连接失败：${String(reason)}`); }
    finally { setSending(false); }
  };

  const save = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    try {
      await api<ProviderRecord>(`/api/settings/providers/${encodeURIComponent(name)}`, {
        method: "PUT", body: JSON.stringify({ name, kind, base_url: baseUrl, model, api_key: apiKey || null }),
      });
      setApiKey("");
      await load();
      setFeedback("配置已保存；密钥保存在系统凭据库。");
    } catch (reason) { setFeedback(`保存失败：${String(reason)}`); }
  };

  const remove = async (providerName: string) => {
    try {
      await api<void>(`/api/settings/providers/${encodeURIComponent(providerName)}`, { method: "DELETE" });
      await load();
      setFeedback("配置已删除。");
    } catch (reason) { setFeedback(`删除失败：${String(reason)}`); }
  };

  return <div className="provider-layout">
    <section className="panel settings-panel">
      <div className="panel-title"><div><Bot size={17} /><h2>模型连接</h2></div></div>
      <form onSubmit={(event) => void save(event)}>
        <label>配置名称<input required pattern="[A-Za-z0-9][A-Za-z0-9_-]*" value={name} onChange={(event) => setName(event.target.value)} placeholder="例如 deepseek" /></label>
        <label>接口类型<select value={kind} onChange={(event) => setKind(event.target.value as ProviderKind)}>
          <option value="openai_compatible">OpenAI 兼容（厂商、中转站、本地服务）</option>
          <option value="anthropic">Anthropic</option><option value="gemini">Gemini</option><option value="ollama">Ollama</option>
        </select></label>
        <label>接口地址<input required type="url" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} placeholder="https://api.example.com/v1" /></label>
        <label>模型名称<input required value={model} onChange={(event) => setModel(event.target.value)} placeholder="模型 ID" /></label>
        <label>API 密钥（可选）<input type="password" autoComplete="new-password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder="本地服务可留空" /></label>
        <button className="primary-button" type="submit">保存模型配置</button>
      </form>
      {feedback && <p role="status">{feedback}</p>}
    </section>
    <section className="panel provider-list"><div className="panel-title"><div><Bot size={17} /><h2>已配置模型</h2></div><span>{items.length} 个</span></div>
      {items.length ? items.map((item) => <div className="provider-row" key={item.name}>
        <div><strong>{item.name}</strong><small>{item.model} · {item.kind} · {item.has_api_key ? "已存密钥" : "无需密钥"}</small><small>{item.base_url}</small></div>
        <button type="button" onClick={() => { setName(item.name); setKind(item.kind); setBaseUrl(item.base_url); setModel(item.model); setApiKey(""); }}>编辑</button>
        <button type="button" onClick={() => void remove(item.name)}>删除</button>
      </div>) : <div className="empty-state">还没有模型配置。可添加云端 API 或本地模型服务。</div>}
    </section>
    {items.length > 0 && <section className="panel provider-playground">
      <div className="panel-title"><div><Bot size={17} /><h2>连接测试</h2></div></div>
      <form onSubmit={(event) => void send(event)}>
        <label>选择配置<select value={selected} onChange={(event) => setSelected(event.target.value)}>
          {items.map((item) => <option value={item.name} key={item.name}>{item.name}</option>)}
        </select></label>
        <label>测试消息<textarea value={message} onChange={(event) => setMessage(event.target.value)} placeholder="输入一条简短消息" /></label>
        <button className="primary-button" type="submit" disabled={sending}>{sending ? "正在连接…" : "发送测试消息"}</button>
      </form>
      {reply && <div className="provider-reply" role="status">{reply}</div>}
    </section>}
  </div>;
}

function NodePanel() {
  return <section className="panel wide-panel"><div className="panel-title"><div><ServerCog size={17} /><h2>执行节点</h2></div></div>
    <div className="node-row"><MonitorCog size={21} /><div><strong>local-node</strong><small>Windows · Python 3.12 · Docker available</small></div><span className="status-pill running">ONLINE</span></div>
  </section>;
}

function SettingsPanel({ onSaved }: { onSaved: () => void }) {
  const [token, setToken] = useState(localStorage.getItem("lfsrc-token") || "");
  const save = () => { localStorage.setItem("lfsrc-token", token); onSaved(); };
  const [scope, setScope] = useState<ScopeRecord | null>(null);
  const [targets, setTargets] = useState("");
  const [prohibited, setProhibited] = useState("");
  const [feedback, setFeedback] = useState("");
  const isDesktop = Boolean(window.pywebview?.api);
  useEffect(() => {
    if (!isDesktop) return;
    void api<ScopeRecord>("/api/settings/scope").then((value) => {
      setScope(value);
      setTargets(value.targets.join("\n"));
      setProhibited(value.prohibited_actions.join("\n"));
    }).catch((reason) => setFeedback(String(reason)));
  }, [isDesktop]);

  const saveScope = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!scope) return;
    try {
      const saved = await api<ScopeRecord>("/api/settings/scope", {
        method: "PUT",
        body: JSON.stringify({
          ...scope,
          targets: targets.split(/\r?\n/).map((value) => value.trim()).filter(Boolean),
          prohibited_actions: prohibited.split(/\r?\n/).map((value) => value.trim()).filter(Boolean),
        }),
      });
      setScope(saved);
      setFeedback("授权范围已保存。");
      onSaved();
    } catch (reason) { setFeedback(`保存失败：${String(reason)}`); }
  };

  if (isDesktop) return <section className="panel settings-panel">
    <div className="panel-title"><div><Settings size={17} /><h2>授权范围</h2></div></div>
    {scope && <form onSubmit={(event) => void saveScope(event)}>
      <label>范围名称<input required value={scope.name} onChange={(event) => setScope({ ...scope, name: event.target.value })} /></label>
      <label>授权目标（每行一个）<textarea required value={targets} onChange={(event) => setTargets(event.target.value)} /></label>
      <label>每分钟请求上限<input type="number" min="1" value={scope.rate_limit.requests} onChange={(event) => setScope({ ...scope, rate_limit: { ...scope.rate_limit, requests: Number(event.target.value) } })} /></label>
      <label>禁止动作（每行一个）<textarea value={prohibited} onChange={(event) => setProhibited(event.target.value)} /></label>
      <button className="primary-button" type="submit">保存授权范围</button>
    </form>}
    {feedback && <p role="status">{feedback}</p>}
  </section>;

  return <section className="panel settings-panel"><div className="panel-title"><div><Settings size={17} /><h2>连接设置</h2></div></div>
    <label>API Token<input type="password" value={token} onChange={(event) => setToken(event.target.value)} placeholder="由部署环境注入" /></label>
    <button className="primary-button" onClick={save}>保存并重连</button>
    <p>Token 仅保存在当前浏览器，不写入项目或事件日志。</p>
  </section>;
}

function EmptyPanel({ icon: Icon, title, text }: { icon: LucideIcon; title: string; text: string }) {
  return <section className="panel empty-panel"><Icon size={28} /><h2>{title}</h2><p>{text}</p></section>;
}
