import { useState, useRef } from "react";
import {
  TrendingUp,
  BookOpen,
  Clock,
  Flame,
  BarChart3,
  ArrowRight,
  Target,
  AlertTriangle,
} from "lucide-react";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Progress } from "../components/ui/progress";
import type { Screen } from "../types";

// ── Types ─────────────────────────────────────────────────────────────

interface AnalyticsProps {
  onNavigate: (screen: Screen) => void;
  dark?: boolean;
}

interface TrendPoint {
  name: string;
  date: string;
  technical: number;
  behavioral: number;
  systemDesign: number;
}

interface TopicRec {
  topic: string;
  category: string;
  priority: "high" | "medium" | "low";
  hours: number;
  sessions: number;
  desc: string;
}

// ── Series config (categorical: indigo → emerald → violet, fixed order) ──

const SERIES = [
  { key: "technical",   label: "Technical",     color: "#7c3aed", darkColor: "#c084fc" },
  { key: "behavioral",  label: "Behavioral",    color: "#10b981", darkColor: "#34d399" },
  { key: "systemDesign",label: "System Design", color: "#4f46e5", darkColor: "#818cf8" },
] as const;

type SeriesKey = typeof SERIES[number]["key"];

// ── Trend data — unique `name` field prevents Recharts key collisions ──

const TREND_DATA: TrendPoint[] = [
  { name: "Wk 1",  date: "May 5",  technical: 55, behavioral: 66, systemDesign: 48 },
  { name: "Wk 2",  date: "May 12", technical: 57, behavioral: 69, systemDesign: 51 },
  { name: "Wk 3",  date: "May 19", technical: 59, behavioral: 70, systemDesign: 53 },
  { name: "Wk 4",  date: "May 26", technical: 61, behavioral: 72, systemDesign: 55 },
  { name: "Wk 5",  date: "Jun 2",  technical: 60, behavioral: 74, systemDesign: 58 },
  { name: "Wk 6",  date: "Jun 9",  technical: 64, behavioral: 75, systemDesign: 60 },
  { name: "Wk 7",  date: "Jun 16", technical: 67, behavioral: 77, systemDesign: 62 },
  { name: "Wk 8",  date: "Jun 23", technical: 66, behavioral: 79, systemDesign: 65 },
  { name: "Wk 9",  date: "Jun 30", technical: 70, behavioral: 81, systemDesign: 67 },
  { name: "Wk 10", date: "Jul 7",  technical: 72, behavioral: 83, systemDesign: 68 },
  { name: "Wk 11", date: "Jul 14", technical: 73, behavioral: 84, systemDesign: 71 },
  { name: "Wk 12", date: "Jul 21", technical: 75, behavioral: 86, systemDesign: 72 },
  { name: "Wk 13", date: "Jul 28", technical: 77, behavioral: 87, systemDesign: 74 },
  { name: "Wk 14", date: "Aug 4",  technical: 79, behavioral: 89, systemDesign: 75 },
  { name: "Wk 15", date: "Aug 11", technical: 80, behavioral: 90, systemDesign: 76 },
  { name: "Wk 16", date: "Aug 18", technical: 82, behavioral: 91, systemDesign: 78 },
];

const RECOMMENDED: TopicRec[] = [
  {
    topic: "Dynamic Programming",
    category: "Algorithms",
    priority: "high",
    hours: 4,
    sessions: 8,
    desc: "Master memoization, tabulation, and optimal substructure. You scored 42 on your last DP session.",
  },
  {
    topic: "Distributed Consensus",
    category: "System Design",
    priority: "high",
    hours: 3,
    sessions: 6,
    desc: "Raft, Paxos, leader election, and quorum-based reads. Core pattern for senior system design.",
  },
  {
    topic: "Behavioral: Conflict Resolution",
    category: "Behavioral",
    priority: "medium",
    hours: 2,
    sessions: 4,
    desc: "Structure conflict stories with clear outcomes using STAR. Weak spot across your last 4 behavioral sessions.",
  },
  {
    topic: "Graph Algorithms",
    category: "Algorithms",
    priority: "medium",
    hours: 3,
    sessions: 6,
    desc: "BFS, DFS, Dijkstra, and topological sort with application to real interview problems.",
  },
  {
    topic: "ML System Design",
    category: "System Design",
    priority: "low",
    hours: 5,
    sessions: 10,
    desc: "Feature pipelines, model training infrastructure, and serving architecture at scale.",
  },
  {
    topic: "Salary Negotiation",
    category: "Behavioral",
    priority: "low",
    hours: 1,
    sessions: 2,
    desc: "Frameworks for negotiating comp packages at FAANG, late-stage startups, and series B.",
  },
];

const CATEGORY_SCORES = [
  { label: "Behavioral",    score: 91, variant: "success" as const },
  { label: "Communication", score: 88, variant: "success" as const },
  { label: "System Design", score: 78, variant: "default" as const },
  { label: "Technical",     score: 82, variant: "default" as const },
  { label: "Dynamic Prog.", score: 42, variant: "warning" as const },
  { label: "Estimation",    score: 57, variant: "warning" as const },
];

// ── Custom SVG multi-line chart (replaces Recharts LineChart) ────────

function TrendChart({
  data,
  hiddenSeries,
  dark,
}: {
  data: TrendPoint[];
  hiddenSeries: Set<SeriesKey>;
  dark: boolean;
}) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const N = data.length;
  const VW = 600, VH = 230;
  const L = 44, R = VW - 10, T = 10, B = VH - 28;
  const W = R - L, H = B - T;
  const Y_MIN = 40, Y_MAX = 100;

  const px = (i: number) => (N < 2 ? L + W / 2 : L + (i / (N - 1)) * W);
  const py = (v: number) => B - ((v - Y_MIN) / (Y_MAX - Y_MIN)) * H;

  const gridColor  = dark ? "#1e293b" : "#f1f5f9";
  const axisColor  = dark ? "#64748b" : "#94a3b8";
  const cursorColor = dark ? "#334155" : "#e2e8f0";

  const yTicks = [40, 60, 80, 100];

  const tickCount = Math.min(N, 5);
  const xTicks = Array.from({ length: tickCount }, (_, i) =>
    i === tickCount - 1 ? N - 1 : Math.round((i / (tickCount - 1)) * (N - 1))
  );
  const uniqueXTicks = [...new Set(xTicks)].sort((a, b) => a - b);

  function handleMouseMove(e: React.MouseEvent<SVGRectElement>) {
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const mx = (e.clientX - rect.left) * (VW / rect.width);
    let closest = 0, closestDist = Infinity;
    for (let i = 0; i < N; i++) {
      const d = Math.abs(px(i) - mx);
      if (d < closestDist) { closestDist = d; closest = i; }
    }
    setHoverIdx(closest);
  }

  const visibleSeries = SERIES.filter(s => !hiddenSeries.has(s.key));
  const hoverPoint = hoverIdx !== null ? data[hoverIdx] : null;
  const ttX = hoverIdx !== null ? px(hoverIdx) : 0;
  const flipTooltip = ttX > 420;

  return (
    <div className="relative w-full" style={{ height: VH }}>
      <svg
        ref={svgRef}
        viewBox={`0 0 ${VW} ${VH}`}
        className="w-full h-full"
        onMouseLeave={() => setHoverIdx(null)}
      >
        {yTicks.map(v => (
          <g key={v}>
            <line x1={L} x2={R} y1={py(v)} y2={py(v)} stroke={gridColor} strokeWidth={1} />
            <text x={L - 6} y={py(v) + 4} textAnchor="end" fontSize={10} fill={axisColor} fontFamily="var(--font-mono)">{v}</text>
          </g>
        ))}

        {uniqueXTicks.map(i => (
          <text key={i} x={px(i)} y={VH - 8} textAnchor="middle" fontSize={10} fill={axisColor} fontFamily="var(--font-mono)">
            {data[i].date}
          </text>
        ))}

        {hoverIdx !== null && (
          <line x1={px(hoverIdx)} x2={px(hoverIdx)} y1={T} y2={B} stroke={cursorColor} strokeWidth={1} />
        )}

        {visibleSeries.map(s => {
          const d = data.map((pt, i) => `${i === 0 ? "M" : "L"} ${px(i).toFixed(1)} ${py(pt[s.key]).toFixed(1)}`).join(" ");
          return (
            <path key={s.key} d={d} fill="none" stroke={dark ? s.darkColor : s.color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
          );
        })}

        {hoverIdx !== null && visibleSeries.map(s => (
          <circle
            key={s.key}
            cx={px(hoverIdx)} cy={py(data[hoverIdx][s.key])} r={5}
            fill={dark ? s.darkColor : s.color}
            stroke={dark ? "#0f172a" : "#ffffff"} strokeWidth={2}
          />
        ))}

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
          <div className="min-w-[152px] rounded-lg border border-border bg-popover px-3.5 py-3 shadow-lg">
            <p className="mb-2.5 text-xs font-medium text-muted-foreground">{hoverPoint.date}</p>
            {visibleSeries.map(s => (
              <div key={s.key} className="flex items-center justify-between gap-5 py-0.5">
                <div className="flex items-center gap-1.5">
                  <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: dark ? s.darkColor : s.color }} />
                  <span className="text-xs text-muted-foreground">{s.label}</span>
                </div>
                <span className="text-xs font-bold tabular-nums text-foreground" style={{ fontFamily: "var(--font-mono)" }}>
                  {hoverPoint[s.key]}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Priority config ───────────────────────────────────────────────────

const PRIORITY_CONFIG = {
  high:   { label: "High",   variant: "destructive" as const, dot: "bg-red-500" },
  medium: { label: "Medium", variant: "warning" as const,     dot: "bg-amber-500" },
  low:    { label: "Low",    variant: "secondary" as const,   dot: "bg-muted-foreground" },
};

// ── Time ranges ───────────────────────────────────────────────────────

type Range = "4w" | "8w" | "16w";
const RANGES: { value: Range; label: string; slice: number }[] = [
  { value: "4w",  label: "4 weeks",  slice: 4  },
  { value: "8w",  label: "8 weeks",  slice: 8  },
  { value: "16w", label: "16 weeks", slice: 16 },
];

// ── Main component ────────────────────────────────────────────────────

export default function Analytics({ onNavigate, dark = false }: AnalyticsProps) {
  const [range, setRange] = useState<Range>("16w");
  const [hiddenSeries, setHiddenSeries] = useState<Set<SeriesKey>>(new Set());

  const rangeConfig = RANGES.find((r) => r.value === range)!;
  const chartData = TREND_DATA.slice(-rangeConfig.slice);

  const latest = TREND_DATA[TREND_DATA.length - 1];
  const earliest = TREND_DATA[0];
  const avgScore = Math.round(
    (latest.technical + latest.behavioral + latest.systemDesign) / 3
  );
  const improvement = Math.round(
    ((latest.technical + latest.behavioral + latest.systemDesign) -
      (earliest.technical + earliest.behavioral + earliest.systemDesign)) / 3
  );

  function toggleSeries(key: SeriesKey) {
    setHiddenSeries((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  }

  const refLine = dark ? "#334155" : "#e2e8f0";

  return (
    <div className="space-y-6 p-6 pb-12">

      {/* ── Header ──────────────────────────────────────────── */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1
            className="text-2xl font-bold tracking-tight text-foreground"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Analytics
          </h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            16 weeks of performance data across all interview categories.
          </p>
        </div>
        <Button onClick={() => onNavigate("create-interview")}>
          <Target size={14} /> New Session
        </Button>
      </div>

      {/* ── KPI strip ───────────────────────────────────────── */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          {
            icon: BarChart3,
            label: "Current Avg",
            value: avgScore,
            sub: "across all categories",
            color: "text-primary",
            bg: "bg-primary/10",
          },
          {
            icon: TrendingUp,
            label: "16-Week Gain",
            value: `+${improvement}`,
            sub: "pts average improvement",
            color: "text-emerald-500",
            bg: "bg-emerald-500/10",
          },
          {
            icon: Flame,
            label: "Best Category",
            value: "Behavioral",
            sub: "91 avg · 12 sessions",
            color: "text-amber-500",
            bg: "bg-amber-500/10",
          },
          {
            icon: AlertTriangle,
            label: "Focus Area",
            value: "Algorithms",
            sub: "2 topics below 60",
            color: "text-red-500",
            bg: "bg-red-500/10",
          },
        ].map(({ icon: Icon, label, value, sub, color, bg }) => (
          <Card key={label}>
            <CardContent className="flex items-center gap-4 p-5">
              <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${bg} ${color}`}>
                <Icon size={18} />
              </div>
              <div className="min-w-0">
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground" style={{ fontFamily: "var(--font-mono)" }}>
                  {label}
                </p>
                <p
                  className="mt-0.5 text-xl font-extrabold tracking-tight text-foreground"
                  style={{ fontFamily: "var(--font-display)" }}
                >
                  {value}
                </p>
                <p className="text-[11px] text-muted-foreground">{sub}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* ── Trend chart + Category breakdown ────────────────── */}
      <div className="grid gap-5 xl:grid-cols-3">

        {/* Trend line chart */}
        <Card className="xl:col-span-2">
          <CardHeader className="pb-3">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <CardTitle className="text-base">Performance Trends</CardTitle>
                <CardDescription className="mt-0.5">
                  Weekly average scores by category
                </CardDescription>
              </div>
              {/* Time range selector */}
              <div className="flex items-center gap-1 rounded-lg border border-border bg-muted p-1 text-xs font-medium">
                {RANGES.map(({ value, label }) => (
                  <button
                    key={value}
                    onClick={() => setRange(value)}
                    className={[
                      "rounded-md px-2.5 py-1.5 transition-all duration-100",
                      range === value
                        ? "bg-card text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground",
                    ].join(" ")}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          </CardHeader>
          <CardContent className="pb-4 pr-4">
            <TrendChart data={chartData} hiddenSeries={hiddenSeries} dark={dark} />

            {/* Custom HTML legend */}
            <div className="mt-3.5 flex items-center justify-center gap-5">
              {SERIES.map(({ key, label, color, darkColor }) => {
                const hidden = hiddenSeries.has(key);
                return (
                  <button
                    key={key}
                    onClick={() => toggleSeries(key)}
                    className={[
                      "flex items-center gap-1.5 rounded px-1.5 py-0.5 text-[11px] font-medium transition-opacity",
                      hidden ? "opacity-35" : "",
                    ].join(" ")}
                    aria-pressed={hidden}
                    title={hidden ? `Show ${label}` : `Hide ${label}`}
                    style={{ fontFamily: "var(--font-mono)" }}
                  >
                    <span
                      className="inline-block h-0.5 w-5 rounded-full"
                      style={{ backgroundColor: dark ? darkColor : color }}
                    />
                    <span className="text-muted-foreground">{label}</span>
                  </button>
                );
              })}
              <div className="flex items-center gap-1.5 text-[11px]" style={{ fontFamily: "var(--font-mono)" }}>
                <span className="inline-block h-px w-5" style={{ borderTop: `1px dashed ${refLine}` }} />
                <span className="text-muted-foreground">Target 85</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Category scores */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">By Category</CardTitle>
            <CardDescription>Current average per skill area</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {CATEGORY_SCORES.map(({ label, score, variant }) => (
              <div key={label} className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-foreground">{label}</span>
                  <span
                    className="text-xs font-bold tabular-nums text-foreground"
                    style={{ fontFamily: "var(--font-mono)" }}
                  >
                    {score}
                  </span>
                </div>
                <Progress value={score} variant={variant} size="sm" />
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* ── Recommended Study Topics ─────────────────────────── */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2
              className="text-base font-semibold text-foreground"
              style={{ fontFamily: "var(--font-display)" }}
            >
              Recommended Study Topics
            </h2>
            <p className="mt-0.5 text-sm text-muted-foreground">
              Ranked by impact on your readiness score.
            </p>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {RECOMMENDED.map(({ topic, category, priority, hours, sessions, desc }) => {
            const pc = PRIORITY_CONFIG[priority];
            return (
              <Card
                key={topic}
                className="group transition-shadow duration-150 hover:shadow-md"
              >
                <CardContent className="flex h-full flex-col gap-3 p-5">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p
                        className="font-semibold text-foreground text-sm leading-tight"
                        style={{ fontFamily: "var(--font-display)" }}
                      >
                        {topic}
                      </p>
                      <p
                        className="mt-0.5 text-[11px] text-muted-foreground"
                        style={{ fontFamily: "var(--font-mono)" }}
                      >
                        {category}
                      </p>
                    </div>
                    <Badge variant={pc.variant} className="shrink-0 text-[10px]">
                      {pc.label}
                    </Badge>
                  </div>

                  <p className="flex-1 text-xs leading-relaxed text-muted-foreground">
                    {desc}
                  </p>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3 text-[11px] text-muted-foreground" style={{ fontFamily: "var(--font-mono)" }}>
                      <span className="flex items-center gap-1">
                        <Clock size={10} /> {hours}h study
                      </span>
                      <span className="flex items-center gap-1">
                        <BookOpen size={10} /> {sessions} sessions
                      </span>
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 px-2 text-xs opacity-0 transition-opacity group-hover:opacity-100"
                      onClick={() => onNavigate("create-interview")}
                    >
                      Start <ArrowRight size={11} />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

    </div>
  );
}
