import {
  BrainCircuit,
  CheckCircle2,
  XCircle,
  RotateCcw,
  LayoutDashboard,
  Mic,
  FileText,
  Clock,
  Building2,
  Lightbulb,
  BookOpen,
  ChevronRight,
  TrendingUp,
} from "lucide-react";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Progress } from "../components/ui/progress";
import type { Screen } from "../types";

// ── Types ─────────────────────────────────────────────────────────────

interface InterviewResultProps {
  onNavigate: (screen: Screen) => void;
  dark?: boolean;
}

// ── Mock session data ─────────────────────────────────────────────────

const SESSION = {
  role: "System Design",
  company: "Stripe",
  date: "Aug 22, 2026",
  mode: "Text" as const,
  duration: "28 min",
  questionCount: 6,
  overallScore: 84,
  previousScore: 77,
};

const RADAR_DATA = [
  { subject: "Technical",     score: 82, fullMark: 100 },
  { subject: "Communication", score: 88, fullMark: 100 },
  { subject: "Problem Solving", score: 81, fullMark: 100 },
  { subject: "Depth",         score: 85, fullMark: 100 },
  { subject: "Confidence",    score: 79, fullMark: 100 },
];

const BREAKDOWN = [
  { label: "Communication",   score: 88, variant: "success" as const },
  { label: "Answer Depth",    score: 85, variant: "success" as const },
  { label: "Technical Accuracy", score: 82, variant: "success" as const },
  { label: "Problem Solving", score: 81, variant: "default" as const },
  { label: "Confidence",      score: 79, variant: "default" as const },
];

const STRENGTHS = [
  {
    title: "Clear problem decomposition",
    desc: "You consistently broke complex systems into manageable components before proposing a solution — textbook approach.",
  },
  {
    title: "Strong trade-off articulation",
    desc: "CAP theorem, consistency models, and latency trade-offs were handled with accuracy and confidence.",
  },
  {
    title: "Structured communication",
    desc: "Answers followed a logical flow: context → constraints → solution → edge cases. The interviewer didn't need to prompt.",
  },
];

const WEAKNESSES = [
  {
    title: "Capacity estimation speed",
    desc: "You hesitated on back-of-envelope calculations. Estimating QPS and storage upfront sharpens every design proposal.",
  },
  {
    title: "Observability coverage",
    desc: "Monitoring, alerting, and distributed tracing were thin. Adding a dedicated observability layer to each design rounds it out.",
  },
];

const AI_SECTIONS = [
  {
    icon: TrendingUp,
    heading: "Overall assessment",
    content:
      "Strong foundation with clear room to grow. A score of 84 reflects genuine competency — your system design instincts are sound. The gap to 90+ is addressable with targeted practice on estimation and observability.",
    items: null,
  },
  {
    icon: CheckCircle2,
    heading: "What worked well",
    content:
      "Your opening — restating requirements, clarifying scale, and identifying constraints — was textbook. API design and data model selection were well-reasoned and you proactively discussed failure modes.",
    items: null,
  },
  {
    icon: Lightbulb,
    heading: "Prioritize before your next session",
    content: null,
    items: [
      "Run 3 capacity estimation drills (QPS → storage → bandwidth). Numbers ground designs and signal confidence to interviewers.",
      "Revisit observability: metrics → distributed tracing → alerting → SLOs. This pattern appears in nearly every senior-level round.",
      "Practice the 'explain it like I'm a PM' variant — your technical depth is there, packaging it for mixed audiences will open more doors.",
    ],
  },
  {
    icon: BookOpen,
    heading: "Recommended reading",
    content: null,
    items: [
      "Designing Data-Intensive Applications — Chapters 5–7 (replication, partitioning, transactions)",
      "Google SRE Book — Chapter 4: Service Level Objectives",
      "System Design Interview Vol. 2 — Chapter on Back-of-Envelope Estimation",
    ],
  },
];

// ── Custom SVG radar (avoids Recharts duplicate-key bug) ─────────────

function SpiderChart({ data, dark }: { data: typeof RADAR_DATA; dark: boolean }) {
  const cx = 150, cy = 108, R = 72, labelR = 95, n = data.length;
  const gridColor  = dark ? "#1e293b" : "#e2e8f0";
  const axisColor  = dark ? "#64748b" : "#94a3b8";
  const fillColor  = dark ? "#a855f7" : "#7c3aed";

  function pt(i: number, r: number): [number, number] {
    const angle = -Math.PI / 2 + (2 * Math.PI / n) * i;
    return [cx + r * Math.cos(angle), cy + r * Math.sin(angle)];
  }

  function polyPts(r: number) {
    return Array.from({ length: n }, (_, i) => pt(i, r).map(v => v.toFixed(1)).join(",")).join(" ");
  }

  const scorePts = data
    .map((d, i) => pt(i, (d.score / 100) * R).map(v => v.toFixed(1)).join(","))
    .join(" ");

  return (
    <svg viewBox="0 0 300 220" width="100%" height={220} aria-label="Skill radar chart">
      {[0.25, 0.5, 0.75, 1].map((level) => (
        <polygon key={`grid-${level}`} points={polyPts(R * level)} fill="none" stroke={gridColor} strokeWidth={1} />
      ))}
      {data.map((_, i) => {
        const [x, y] = pt(i, R);
        return <line key={`axis-${i}`} x1={cx} y1={cy} x2={x.toFixed(1)} y2={y.toFixed(1)} stroke={gridColor} strokeWidth={1} />;
      })}
      <polygon points={scorePts} fill={fillColor} fillOpacity={0.15} stroke={fillColor} strokeWidth={2} strokeLinejoin="round" />
      {data.map((d, i) => {
        const [x, y] = pt(i, (d.score / 100) * R);
        return <circle key={`dot-${i}`} cx={x.toFixed(1)} cy={y.toFixed(1)} r={4} fill={fillColor} />;
      })}
      {data.map((d, i) => {
        const [lx, ly] = pt(i, labelR);
        const anchor = Math.abs(lx - cx) < 5 ? "middle" : lx > cx ? "start" : "end";
        return (
          <text key={`label-${d.subject}`} x={lx.toFixed(1)} y={(ly + 4).toFixed(1)} textAnchor={anchor} fontSize={10} fill={axisColor} fontFamily="var(--font-mono)">
            {d.subject}
          </text>
        );
      })}
    </svg>
  );
}

// ── Score gauge (SVG arc) ─────────────────────────────────────────────

function ScoreMeter({ score }: { score: number }) {
  const R = 78;
  const cx = 100;
  const cy = 96;
  const sw = 13;

  const fillColor =
    score >= 80 ? "#10b981" : score >= 60 ? "#f59e0b" : "#ef4444";

  const angle = (Math.PI * Math.max(0, Math.min(score, 100))) / 100;
  const fillX = (cx - R * Math.cos(angle)).toFixed(3);
  const fillY = (cy - R * Math.sin(angle)).toFixed(3);

  const trackD = `M ${cx - R} ${cy} A ${R} ${R} 0 0 1 ${cx + R} ${cy}`;
  const fillD  = `M ${cx - R} ${cy} A ${R} ${R} 0 0 1 ${fillX} ${fillY}`;
  const fullD  = trackD;

  const grade =
    score >= 90 ? "A"
    : score >= 80 ? "B"
    : score >= 70 ? "C"
    : score >= 60 ? "D"
    : "F";

  return (
    <div className="flex flex-col items-center">
      <svg
        width="200"
        height="110"
        viewBox="0 0 200 110"
        aria-label={`Score: ${score} out of 100, grade ${grade}`}
      >
        {/* Track */}
        <path
          d={trackD}
          fill="none"
          stroke="currentColor"
          strokeWidth={sw}
          strokeLinecap="round"
          className="text-secondary"
        />
        {/* Fill arc */}
        {score > 0 && score < 100 && (
          <path
            d={fillD}
            fill="none"
            stroke={fillColor}
            strokeWidth={sw}
            strokeLinecap="round"
          />
        )}
        {score >= 100 && (
          <path
            d={fullD}
            fill="none"
            stroke={fillColor}
            strokeWidth={sw}
            strokeLinecap="round"
          />
        )}
        {/* Needle cap dot */}
        {score > 0 && (
          <circle
            cx={score >= 100 ? cx + R : Number(fillX)}
            cy={score >= 100 ? cy : Number(fillY)}
            r={sw / 2 + 2.5}
            fill={fillColor}
          />
        )}
        {/* Score number */}
        <text
          x={cx}
          y={68}
          textAnchor="middle"
          fontSize="38"
          fontWeight="800"
          letterSpacing="-0.04em"
          fill="currentColor"
          fontFamily="var(--font-display)"
        >
          {score}
        </text>
        <text
          x={cx}
          y={86}
          textAnchor="middle"
          fontSize="11"
          fontWeight="500"
          fill="currentColor"
          opacity={0.45}
          fontFamily="var(--font-mono)"
        >
          / 100
        </text>
      </svg>

      {/* Grade badge below SVG */}
      <div className="mt-1 flex items-center gap-2">
        <span
          className="text-2xl font-extrabold"
          style={{ color: fillColor, fontFamily: "var(--font-display)" }}
        >
          {grade}
        </span>
        <div className="text-left">
          <p className="text-xs font-semibold text-foreground leading-tight">
            {score >= 80 ? "Strong" : score >= 60 ? "Developing" : "Needs Work"}
          </p>
          <p className="text-[10px] text-muted-foreground" style={{ fontFamily: "var(--font-mono)" }}>
            +{score - SESSION.previousScore} vs last session
          </p>
        </div>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────

export default function InterviewResult({ onNavigate, dark = false }: InterviewResultProps) {
  return (
    <div className="mx-auto max-w-4xl space-y-6 px-5 py-8 pb-12">

      {/* ── Session header ───────────────────────────────────── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <h1
              className="text-2xl font-bold tracking-tight text-foreground"
              style={{ fontFamily: "var(--font-display)" }}
            >
              {SESSION.role}
            </h1>
            <Badge variant={SESSION.mode === "Voice" ? "violet" : "default"}>
              {SESSION.mode === "Voice" ? <Mic size={10} /> : <FileText size={10} />}
              {SESSION.mode}
            </Badge>
          </div>
          <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground" style={{ fontFamily: "var(--font-mono)" }}>
            <span className="flex items-center gap-1"><Building2 size={11} />{SESSION.company}</span>
            <span className="flex items-center gap-1"><Clock size={11} />{SESSION.duration}</span>
            <span>{SESSION.questionCount} questions</span>
            <span>{SESSION.date}</span>
          </div>
        </div>
        <div className="flex gap-2 shrink-0">
          <Button variant="outline" size="sm" onClick={() => onNavigate("create-interview")}>
            <RotateCcw size={13} /> Retry
          </Button>
          <Button variant="ghost" size="sm" onClick={() => onNavigate("dashboard")}>
            <LayoutDashboard size={13} /> Dashboard
          </Button>
        </div>
      </div>

      {/* ── Score meter + Radar ──────────────────────────────── */}
      <div className="grid gap-4 sm:grid-cols-5">

        {/* Meter card */}
        <Card className="sm:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Overall Score</CardTitle>
          </CardHeader>
          <CardContent className="flex justify-center pb-5">
            <ScoreMeter score={SESSION.overallScore} />
          </CardContent>
        </Card>

        {/* Radar card — single series, no legend needed; title names it */}
        <Card className="sm:col-span-3">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Skill Breakdown</CardTitle>
          </CardHeader>
          <CardContent className="pb-3">
            <SpiderChart data={RADAR_DATA} dark={dark} />
          </CardContent>
        </Card>
      </div>

      {/* ── Breakdown progress bars ──────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Score Breakdown</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {BREAKDOWN.map(({ label, score, variant }) => (
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
              <Progress value={score} variant={variant} size="md" />
            </div>
          ))}
        </CardContent>
      </Card>

      {/* ── Strengths + Weaknesses ───────────────────────────── */}
      <div className="grid gap-4 sm:grid-cols-2">

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <CheckCircle2 size={15} className="text-emerald-500" />
              Strengths
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {STRENGTHS.map(({ title, desc }) => (
              <div key={title} className="flex gap-3">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-500">
                  <CheckCircle2 size={11} />
                </span>
                <div>
                  <p className="text-sm font-semibold text-foreground">{title}</p>
                  <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{desc}</p>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <XCircle size={15} className="text-amber-500" />
              Areas to Improve
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {WEAKNESSES.map(({ title, desc }) => (
              <div key={title} className="flex gap-3">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-amber-500/10 text-amber-500">
                  <XCircle size={11} />
                </span>
                <div>
                  <p className="text-sm font-semibold text-foreground">{title}</p>
                  <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{desc}</p>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* ── AI Coach feedback ────────────────────────────────── */}
      <Card className="border-primary/20 bg-primary/[0.03]">
        <CardHeader className="pb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
              <BrainCircuit size={17} />
            </div>
            <div>
              <CardTitle className="text-base">AI Coach Analysis</CardTitle>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Personalized feedback based on your responses
              </p>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-5">
          {AI_SECTIONS.map(({ icon: Icon, heading, content, items }) => (
            <div key={heading} className="flex gap-3.5">
              <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                <Icon size={13} />
              </span>
              <div className="min-w-0 flex-1">
                <p
                  className="mb-1.5 text-sm font-semibold text-foreground"
                  style={{ fontFamily: "var(--font-display)" }}
                >
                  {heading}
                </p>
                {content && (
                  <p className="text-sm leading-relaxed text-muted-foreground">{content}</p>
                )}
                {items && (
                  <ul className="space-y-1.5">
                    {items.map((item, i) => (
                      <li
                        key={i}
                        className="flex items-start gap-2 text-sm text-muted-foreground"
                      >
                        <ChevronRight
                          size={13}
                          className="mt-0.5 shrink-0 text-primary"
                        />
                        {item}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* ── Actions ──────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
        <p className="text-xs text-muted-foreground" style={{ fontFamily: "var(--font-mono)" }}>
          session · aug_22_system_design_stripe
        </p>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => onNavigate("results")}>
            View History
          </Button>
          <Button onClick={() => onNavigate("create-interview")}>
            Next Interview <ChevronRight size={14} />
          </Button>
        </div>
      </div>

    </div>
  );
}
