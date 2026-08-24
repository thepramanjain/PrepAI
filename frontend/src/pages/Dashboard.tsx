import { useState, useRef } from "react";
import {
  FileText,
  Mic,
  Award,
  Flame,
  Hash,
  ExternalLink,
  Target,
  TrendingUp,
  TrendingDown,
  Minus,
} from "lucide-react";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import type { Screen } from "../types";

// ── Types ─────────────────────────────────────────────────────────────

interface DashboardProps {
  onNavigate: (screen: Screen) => void;
  dark?: boolean;
}

interface ChartPoint {
  name: string;
  date: string;
  score: number;
  mode: "Text" | "Voice";
}

interface SessionRow {
  id: number;
  date: string;
  role: string;
  company: string;
  mode: "Text" | "Voice";
  score: number;
  duration: string;
}

interface SkillChip {
  name: string;
  score: number;
  category: string;
}

// ── Mock data ─────────────────────────────────────────────────────────

const CHART_DATA: ChartPoint[] = [
  { name: "Session 1",  date: "Jul 8",  score: 58, mode: "Text" },
  { name: "Session 2",  date: "Jul 11", score: 63, mode: "Voice" },
  { name: "Session 3",  date: "Jul 14", score: 60, mode: "Text" },
  { name: "Session 4",  date: "Jul 17", score: 69, mode: "Voice" },
  { name: "Session 5",  date: "Jul 20", score: 72, mode: "Text" },
  { name: "Session 6",  date: "Jul 23", score: 70, mode: "Voice" },
  { name: "Session 7",  date: "Jul 26", score: 76, mode: "Text" },
  { name: "Session 8",  date: "Jul 29", score: 80, mode: "Voice" },
  { name: "Session 9",  date: "Aug 2",  score: 78, mode: "Text" },
  { name: "Session 10", date: "Aug 6",  score: 83, mode: "Voice" },
  { name: "Session 11", date: "Aug 10", score: 82, mode: "Text" },
  { name: "Session 12", date: "Aug 14", score: 87, mode: "Voice" },
  { name: "Session 13", date: "Aug 17", score: 85, mode: "Text" },
  { name: "Session 14", date: "Aug 20", score: 91, mode: "Voice" },
  { name: "Session 15", date: "Aug 22", score: 84, mode: "Text" },
];

const SESSIONS: SessionRow[] = [
  { id: 1, date: "Aug 22", role: "System Design",          company: "Stripe",    mode: "Text",  score: 84, duration: "28 min" },
  { id: 2, date: "Aug 20", role: "Behavioral — Leadership", company: "Anthropic", mode: "Voice", score: 91, duration: "34 min" },
  { id: 3, date: "Aug 17", role: "LC Hard — Dynamic Prog.", company: "Google",    mode: "Text",  score: 55, duration: "45 min" },
  { id: 4, date: "Aug 14", role: "System Design",           company: "Meta",      mode: "Voice", score: 87, duration: "40 min" },
  { id: 5, date: "Aug 10", role: "Behavioral — Culture",   company: "Netflix",   mode: "Text",  score: 82, duration: "26 min" },
  { id: 6, date: "Aug 6",  role: "System Design — Cache",  company: "Stripe",    mode: "Voice", score: 83, duration: "38 min" },
  { id: 7, date: "Aug 2",  role: "LC Medium — DP",          company: "Amazon",    mode: "Text",  score: 63, duration: "32 min" },
  { id: 8, date: "Jul 29", role: "Behavioral — Conflict",  company: "Figma",     mode: "Voice", score: 80, duration: "30 min" },
];

const WEAK_SKILLS: SkillChip[] = [
  { name: "Dynamic Programming",   score: 42, category: "Algorithms" },
  { name: "Distributed Systems",   score: 51, category: "System Design" },
  { name: "System Scalability",    score: 54, category: "System Design" },
  { name: "Estimation & Sizing",   score: 57, category: "System Design" },
  { name: "Concurrency",           score: 60, category: "Algorithms" },
  { name: "Negotiation",           score: 63, category: "Behavioral" },
  { name: "ML Fundamentals",       score: 65, category: "Technical" },
];

// ── Helpers ───────────────────────────────────────────────────────────

function scoreVariant(score: number): "success" | "warning" | "destructive" {
  if (score >= 80) return "success";
  if (score >= 60) return "warning";
  return "destructive";
}

function scoreTailwind(score: number): string {
  if (score >= 80) return "text-emerald-600 dark:text-emerald-400";
  if (score >= 60) return "text-amber-600 dark:text-amber-400";
  return "text-red-600 dark:text-red-400";
}

function skillDotColor(score: number): string {
  if (score >= 60) return "bg-amber-500";
  return "bg-red-500";
}

const avg = Math.round(CHART_DATA.reduce((s, p) => s + p.score, 0) / CHART_DATA.length);
const best = Math.max(...CHART_DATA.map((p) => p.score));
const bestSession = SESSIONS.find((s) => s.score === best)!;
const totalSessions = 47;

// ── Circular Progress ─────────────────────────────────────────────────

function CircularProgress({ value, size = 88, strokeWidth = 8 }: { value: number; size?: number; strokeWidth?: number }) {
  const r = (size - strokeWidth) / 2;
  const cx = size / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ * (1 - Math.max(0, Math.min(value, 100)) / 100);

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden role="img">
      <defs>
        <linearGradient id="avg-grad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#6366f1" />
          <stop offset="100%" stopColor="#8b5cf6" />
        </linearGradient>
      </defs>
      {/* Track */}
      <circle
        cx={cx} cy={cx} r={r}
        fill="none"
        strokeWidth={strokeWidth}
        stroke="currentColor"
        className="text-secondary"
      />
      {/* Arc */}
      <circle
        cx={cx} cy={cx} r={r}
        fill="none"
        stroke="url(#avg-grad)"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray={circ}
        strokeDashoffset={offset}
        transform={`rotate(-90 ${cx} ${cx})`}
        style={{ transition: "stroke-dashoffset 1s cubic-bezier(0.4, 0, 0.2, 1)" }}
      />
    </svg>
  );
}

// ── Custom SVG area chart (replaces Recharts AreaChart) ──────────────

function ScoreChart({ data, dark }: { data: ChartPoint[]; dark: boolean }) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const N = data.length;
  const VW = 600, VH = 220;
  const L = 44, R = VW - 8, T = 8, B = VH - 20;
  const W = R - L, H = B - T;
  const Y_MIN = 40, Y_MAX = 100;

  const lineColor  = dark ? "#818cf8" : "#6366f1";
  const gridColor  = dark ? "#1e293b" : "#f1f5f9";
  const axisColor  = dark ? "#64748b" : "#94a3b8";
  const cursorColor = dark ? "#334155" : "#e2e8f0";
  const bgDot      = dark ? "#0f172a" : "#ffffff";

  const px = (i: number) => N < 2 ? L + W / 2 : L + (i / (N - 1)) * W;
  const py = (v: number) => B - ((v - Y_MIN) / (Y_MAX - Y_MIN)) * H;

  const yTicks = [40, 60, 80, 100];
  const xTickCount = Math.min(N, 6);
  const xTickIdxs = N <= 6
    ? data.map((_, i) => i)
    : Array.from({ length: xTickCount }, (_, i) =>
        i === xTickCount - 1 ? N - 1 : Math.round((i / (xTickCount - 1)) * (N - 1))
      );
  const uniqueXTicks = [...new Set(xTickIdxs)].sort((a, b) => a - b);

  function handleMouseMove(e: React.MouseEvent<SVGRectElement>) {
    const svg = svgRef.current;
    if (!svg || N === 0) return;
    const rect = svg.getBoundingClientRect();
    const mx = (e.clientX - rect.left) * (VW / rect.width);
    let closest = 0, closestDist = Infinity;
    for (let i = 0; i < N; i++) {
      const d = Math.abs(px(i) - mx);
      if (d < closestDist) { closestDist = d; closest = i; }
    }
    setHoverIdx(closest);
  }

  const linePath = N > 0
    ? data.map((pt, i) => `${i === 0 ? "M" : "L"} ${px(i).toFixed(1)} ${py(pt.score).toFixed(1)}`).join(" ")
    : "";
  const areaPath = N > 1
    ? `${linePath} L ${px(N - 1).toFixed(1)} ${B} L ${px(0).toFixed(1)} ${B} Z`
    : "";

  const hoverPoint = hoverIdx !== null ? data[hoverIdx] : null;
  const ttX = hoverIdx !== null ? px(hoverIdx) : 0;
  const flipTooltip = ttX > 430;

  function scoreColor(score: number) {
    return score >= 80 ? "#10b981" : score >= 60 ? "#f59e0b" : "#ef4444";
  }

  if (N === 0) {
    return (
      <div className="flex h-[220px] items-center justify-center text-sm text-muted-foreground">
        No sessions match this filter.
      </div>
    );
  }

  return (
    <div className="relative w-full" style={{ height: VH }}>
      <svg ref={svgRef} viewBox={`0 0 ${VW} ${VH}`} className="w-full h-full" onMouseLeave={() => setHoverIdx(null)}>
        <defs>
          <linearGradient id="dash-area-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor={lineColor} stopOpacity={0.18} />
            <stop offset="95%" stopColor={lineColor} stopOpacity={0} />
          </linearGradient>
        </defs>

        {yTicks.map(v => (
          <g key={v}>
            <line x1={L} x2={R} y1={py(v)} y2={py(v)} stroke={gridColor} strokeWidth={1} />
            <text x={L - 6} y={py(v) + 4} textAnchor="end" fontSize={10} fill={axisColor} fontFamily="var(--font-mono)">{v}</text>
          </g>
        ))}

        {uniqueXTicks.map(i => (
          <text key={i} x={px(i)} y={VH - 4} textAnchor="middle" fontSize={10} fill={axisColor} fontFamily="var(--font-mono)">
            {data[i].date}
          </text>
        ))}

        {hoverIdx !== null && (
          <line x1={px(hoverIdx)} x2={px(hoverIdx)} y1={T} y2={B} stroke={cursorColor} strokeWidth={1} />
        )}

        {N > 1 && <path d={areaPath} fill="url(#dash-area-fill)" />}
        <path d={linePath} fill="none" stroke={lineColor} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />

        {data.map((pt, i) => (
          <circle key={i} cx={px(i)} cy={py(pt.score)} r={3.5} fill={lineColor} />
        ))}

        {hoverIdx !== null && (
          <circle cx={px(hoverIdx)} cy={py(data[hoverIdx].score)} r={5.5} fill={lineColor} stroke={bgDot} strokeWidth={2} />
        )}

        <rect x={L} y={T} width={W} height={H} fill="transparent" style={{ cursor: "crosshair" }} onMouseMove={handleMouseMove} />
      </svg>

      {hoverPoint && hoverIdx !== null && (
        <div
          className="pointer-events-none absolute top-4 z-10"
          style={{
            left:  flipTooltip ? "auto" : `calc(${(px(hoverIdx) / VW) * 100}% + 12px)`,
            right: flipTooltip ? `calc(${((VW - px(hoverIdx)) / VW) * 100}% + 12px)` : "auto",
          }}
        >
          <div className="rounded-lg border border-border bg-popover px-3.5 py-3 shadow-lg">
            <p className="mb-1.5 text-xs font-medium text-muted-foreground">{hoverPoint.date}</p>
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-bold tabular-nums" style={{ color: scoreColor(hoverPoint.score), fontFamily: "var(--font-display)" }}>
                {hoverPoint.score}
              </span>
              <span className="text-xs text-muted-foreground">/100</span>
            </div>
            <div className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
              {hoverPoint.mode === "Text" ? <FileText size={10} /> : <Mic size={10} />}
              {hoverPoint.mode} interview
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Trend indicator ───────────────────────────────────────────────────

function Trend({ value, label }: { value: string; label: string }) {
  const positive = value.startsWith("+");
  const neutral = value.startsWith("—") || value === "0";
  return (
    <div className={`flex items-center gap-1 text-xs font-medium ${
      neutral ? "text-muted-foreground" : positive ? "text-emerald-600 dark:text-emerald-400" : "text-red-500"
    }`}>
      {neutral ? <Minus size={11} /> : positive ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
      {value} <span className="font-normal text-muted-foreground">{label}</span>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────

type FilterMode = "all" | "text" | "voice";

export default function Dashboard({ onNavigate, dark = false }: DashboardProps) {
  const [filter, setFilter] = useState<FilterMode>("all");
  const [activeSkills, setActiveSkills] = useState<Set<string>>(new Set());

  const filteredChart = filter === "all"
    ? CHART_DATA
    : CHART_DATA.filter((d) => d.mode.toLowerCase() === filter);

  function toggleSkill(name: string) {
    setActiveSkills((prev) => {
      const next = new Set(prev);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });
  }

  // colors used in chart legend below the card
  const refLine = dark ? "#334155" : "#e2e8f0";
  const line    = dark ? "#818cf8" : "#6366f1";

  return (
    <div className="space-y-6 p-6 pb-10">

      {/* ── Page header ─────────────────────────────────────── */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground" style={{ fontFamily: "var(--font-display)" }}>
            Dashboard
          </h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Google onsite in <span className="font-semibold text-foreground">6 days</span> — keep the momentum.
          </p>
        </div>
        <Button onClick={() => onNavigate("create-interview")}>
          <Target size={14} /> New Interview
        </Button>
      </div>

      {/* ── Metric cards ────────────────────────────────────── */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">

        {/* Total Interviews */}
        <Card className="hover:-translate-y-0.5 hover:shadow-md">
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground" style={{ fontFamily: "var(--font-mono)" }}>
                  Total Interviews
                </p>
                <p className="mt-2 text-4xl font-extrabold tabular-nums tracking-tighter text-foreground" style={{ fontFamily: "var(--font-display)" }}>
                  {totalSessions}
                </p>
                <Trend value="+3" label="this week" />
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Hash size={18} />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Average Score — circular progress */}
        <Card className="relative overflow-hidden hover:-translate-y-0.5 hover:shadow-md">
          <CardContent className="p-5">
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground" style={{ fontFamily: "var(--font-mono)" }}>
              Average Score
            </p>
            <div className="mt-2 flex items-center gap-4">
              <div className="relative shrink-0">
                <CircularProgress value={avg} size={88} strokeWidth={8} />
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-xl font-extrabold tabular-nums tracking-tight leading-none text-foreground" style={{ fontFamily: "var(--font-display)" }}>
                    {avg}
                  </span>
                  <span className="text-[10px] text-muted-foreground" style={{ fontFamily: "var(--font-mono)" }}>
                    /100
                  </span>
                </div>
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground">Good standing</p>
                <p className="mt-0.5 text-xs text-muted-foreground">Up 4 pts from last month</p>
                <Trend value="+4" label="vs. Jul avg" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Best Score */}
        <Card className="hover:-translate-y-0.5 hover:shadow-md">
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground" style={{ fontFamily: "var(--font-mono)" }}>
                  Best Score
                </p>
                <p className="mt-2 text-4xl font-extrabold tabular-nums tracking-tighter text-emerald-500" style={{ fontFamily: "var(--font-display)" }}>
                  {best}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {bestSession?.role} · {bestSession?.date}
                </p>
                <Trend value="+8" label="vs. avg" />
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-500">
                <Award size={18} />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Streak */}
        <Card className="hover:-translate-y-0.5 hover:shadow-md">
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground" style={{ fontFamily: "var(--font-mono)" }}>
                  Practice Streak
                </p>
                <p className="mt-2 text-4xl font-extrabold tabular-nums tracking-tighter text-amber-500" style={{ fontFamily: "var(--font-display)" }}>
                  12
                </p>
                <p className="mt-1 text-xs text-muted-foreground">days in a row</p>
                <Trend value="+5" label="vs. best" />
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-500/10 text-amber-500">
                <Flame size={18} />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ── Chart + Skills ──────────────────────────────────── */}
      <div className="grid gap-6 xl:grid-cols-3">

        {/* Performance Chart */}
        <Card className="xl:col-span-2 hover:-translate-y-0.5 hover:shadow-md">
          <CardHeader className="pb-3">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <CardTitle className="text-base">Score Progression</CardTitle>
                <CardDescription className="mt-0.5">Last 15 sessions · target 85</CardDescription>
              </div>
              {/* Filter toggle */}
              <div className="flex items-center gap-1 rounded-lg border border-border bg-muted p-1 text-xs font-medium">
                {(["all", "text", "voice"] as const).map((mode) => (
                  <button
                    key={mode}
                    onClick={() => setFilter(mode)}
                    className={[
                      "rounded-md px-3 py-1.5 capitalize transition-all duration-100",
                      filter === mode
                        ? "bg-card text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground",
                    ].join(" ")}
                  >
                    {mode === "all" ? "All" : mode === "text" ? "Text" : "Voice"}
                  </button>
                ))}
              </div>
            </div>
          </CardHeader>
          <CardContent className="pb-5 pr-4">
            <ScoreChart data={filteredChart} dark={dark} />
            <div className="mt-3 flex items-center justify-center gap-5">
              <div className="flex items-center gap-1.5">
                <span className="inline-block h-0.5 w-5 rounded-full" style={{ backgroundColor: line }} />
                <span className="text-[11px] text-muted-foreground" style={{ fontFamily: "var(--font-mono)" }}>
                  Interview score
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="inline-block h-px w-5" style={{ borderTop: `1px dashed ${refLine}` }} />
                <span className="text-[11px] text-muted-foreground" style={{ fontFamily: "var(--font-mono)" }}>
                  Target 85
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Weakest Skills */}
        <Card className="hover:-translate-y-0.5 hover:shadow-md">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Weakest Skills</CardTitle>
            <CardDescription>Tap to focus your next session</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2.5">
            {WEAK_SKILLS.map(({ name, score, category }) => {
              const active = activeSkills.has(name);
              return (
                <button
                  key={name}
                  onClick={() => toggleSkill(name)}
                  className={[
                    "group flex w-full items-center gap-3 rounded-lg border px-3 py-2.5 text-left transition-all duration-150",
                    active
                      ? "border-primary/40 bg-primary/8 ring-1 ring-primary/20"
                      : "border-border bg-transparent hover:border-primary/30 hover:bg-accent/40",
                  ].join(" ")}
                  aria-pressed={active}
                >
                  <span className={`h-2 w-2 shrink-0 rounded-full ${skillDotColor(score)}`} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-foreground">{name}</p>
                    <p className="text-[10px] text-muted-foreground" style={{ fontFamily: "var(--font-mono)" }}>
                      {category}
                    </p>
                  </div>
                  <span
                    className={`shrink-0 text-sm font-bold tabular-nums ${scoreTailwind(score)}`}
                    style={{ fontFamily: "var(--font-mono)" }}
                  >
                    {score}
                  </span>
                </button>
              );
            })}
            {activeSkills.size > 0 && (
              <div className="pt-1">
                <Button
                  size="sm"
                  className="w-full"
                  onClick={() => {
                    setActiveSkills(new Set());
                    onNavigate("create-interview");
                  }}
                >
                  Practice {activeSkills.size} selected skill{activeSkills.size > 1 ? "s" : ""}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ── Recent Interviews table ──────────────────────────── */}
      <Card className="hover:-translate-y-0.5 hover:shadow-md">
        <CardHeader className="pb-0">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base">Recent Interviews</CardTitle>
              <CardDescription className="mt-0.5">Your last 8 sessions</CardDescription>
            </div>
            <Button variant="ghost" size="sm" onClick={() => onNavigate("results")}>
              View all <ExternalLink size={12} />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {/* Table header */}
          <div className="grid grid-cols-[1fr_auto_auto_auto_auto] gap-x-4 border-b border-border px-5 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground sm:grid-cols-[1fr_120px_90px_80px_90px_auto]" style={{ fontFamily: "var(--font-mono)" }}>
            <span>Session</span>
            <span className="hidden sm:block">Company</span>
            <span className="hidden sm:block">Mode</span>
            <span className="hidden sm:block">Duration</span>
            <span>Score</span>
            <span className="text-right">Action</span>
          </div>

          {/* Rows */}
          <div className="divide-y divide-border">
            {SESSIONS.map(({ id, date, role, company, mode, score, duration }) => (
              <div
                key={id}
                className="grid grid-cols-[1fr_auto_auto_auto_auto] items-center gap-x-4 px-5 py-3.5 transition-colors hover:bg-muted/30 sm:grid-cols-[1fr_120px_90px_80px_90px_auto]"
              >
                {/* Role + date */}
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-foreground">{role}</p>
                  <p className="text-xs text-muted-foreground" style={{ fontFamily: "var(--font-mono)" }}>
                    {date}
                  </p>
                </div>

                {/* Company */}
                <span className="hidden truncate text-sm text-muted-foreground sm:block">
                  {company}
                </span>

                {/* Mode */}
                <div className="hidden items-center gap-1.5 sm:flex">
                  <div className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-xs ${
                    mode === "Text"
                      ? "bg-primary/10 text-primary"
                      : "bg-purple-600/10 text-purple-600 dark:text-purple-400"
                  }`}>
                    {mode === "Text" ? <FileText size={12} /> : <Mic size={12} />}
                  </div>
                  <span className="text-xs text-muted-foreground">{mode}</span>
                </div>

                {/* Duration */}
                <span className="hidden text-xs tabular-nums text-muted-foreground sm:block" style={{ fontFamily: "var(--font-mono)" }}>
                  {duration}
                </span>

                {/* Score */}
                <div className="flex items-center">
                  <Badge variant={scoreVariant(score)} className="tabular-nums" style={{ fontFamily: "var(--font-mono)" }}>
                    {score}
                  </Badge>
                </div>

                {/* Action */}
                <div className="flex justify-end">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 px-2 text-xs"
                    onClick={() => onNavigate("results")}
                  >
                    <span className="hidden sm:inline">View Feedback</span>
                    <ExternalLink size={11} className="sm:ml-1" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

    </div>
  );
}
