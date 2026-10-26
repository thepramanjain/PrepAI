import { useState, useEffect } from "react";
import {
  BrainCircuit,
  CheckCircle2,
  XCircle,
  RotateCcw,
  LayoutDashboard,
  Mic,
  FileText,
  Clock,
  Briefcase,
  Lightbulb,
  ChevronRight,
  TrendingUp,
  Loader2,
  Sparkles,
} from "lucide-react";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Progress } from "../components/ui/progress";
import type { Screen } from "../types";
import { getFeedback, evaluateInterview, type FeedbackResponse } from "../services/feedback.api";
import * as interviewApi from "../services/interview.api";

// ── Types ─────────────────────────────────────────────────────────────

interface InterviewResultProps {
  onNavigate: (screen: Screen, state?: Record<string, any>) => void;
  dark?: boolean;
  interviewId?: string;
}

// ── Custom SVG radar ──────────────────────────────────────────────────

function SpiderChart({
  data,
  dark,
}: {
  data: Array<{ subject: string; score: number; fullMark: number }>;
  dark: boolean;
}) {
  const cx = 150, cy = 108, R = 72, labelR = 95;
  const n = Math.max(data.length, 3);
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
    .map((d, i) => pt(i, ((d.score || 0) / 100) * R).map(v => v.toFixed(1)).join(","))
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
      {data.length > 0 && (
        <polygon points={scorePts} fill={fillColor} fillOpacity={0.18} stroke={fillColor} strokeWidth={2} strokeLinejoin="round" />
      )}
      {data.map((d, i) => {
        const [x, y] = pt(i, ((d.score || 0) / 100) * R);
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
        <path
          d={trackD}
          fill="none"
          stroke="currentColor"
          strokeWidth={sw}
          strokeLinecap="round"
          className="text-secondary"
        />
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
        {score > 0 && (
          <circle
            cx={score >= 100 ? cx + R : Number(fillX)}
            cy={score >= 100 ? cy : Number(fillY)}
            r={sw / 2 + 2.5}
            fill={fillColor}
          />
        )}
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
            Overall Performance
          </p>
        </div>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────

export default function InterviewResult({ onNavigate, dark = false, interviewId }: InterviewResultProps) {
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<FeedbackResponse | null>(null);
  const [interview, setInterview] = useState<interviewApi.InterviewDoc | null>(null);

  useEffect(() => {
    let active = true;

    async function loadData() {
      setLoading(true);
      setError(null);

      try {
        let currentId = interviewId;

        // If no interviewId passed, find the most recent completed interview
        if (!currentId) {
          const listRes = await interviewApi.getInterviews(1, 10);
          const interviews = listRes?.items || [];
          if (interviews.length > 0) {
            const completed = interviews.find((i: any) => i.status === "completed") || interviews[0];
            currentId = completed.id || completed._id;
          }
        }

        if (!currentId) {
          if (active) {
            setInterview(null);
            setFeedback(null);
            setLoading(false);
          }
          return;
        }

        // Fetch interview details
        const intDoc = await interviewApi.getInterview(currentId);
        if (active) setInterview(intDoc);

        // Try to fetch feedback; if 404, trigger evaluation
        try {
          const fb = await getFeedback(currentId);
          if (active) setFeedback(fb);
        } catch (fbErr: any) {
          if (fbErr?.response?.status === 404) {
            if (active) setEvaluating(true);
            try {
              const evaluated = await evaluateInterview(currentId);
              if (active) setFeedback(evaluated);
            } catch (evalErr: any) {
              if (active) {
                console.error("Evaluation failed:", evalErr);
                setError(evalErr?.response?.data?.detail || "Could not generate AI feedback for this interview.");
              }
            } finally {
              if (active) setEvaluating(false);
            }
          } else {
            throw fbErr;
          }
        }
      } catch (err: any) {
        if (active) {
          console.error("Failed to load interview results:", err);
          setError(err?.response?.data?.detail || "Failed to load interview results.");
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    loadData();
    return () => { active = false; };
  }, [interviewId]);

  if (loading || evaluating) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 text-center">
        <Loader2 size={36} className="animate-spin text-primary" />
        <p className="text-base font-semibold text-foreground" style={{ fontFamily: "var(--font-display)" }}>
          {evaluating ? "AI Coach is analyzing your answers..." : "Loading interview feedback..."}
        </p>
        <p className="max-w-xs text-xs text-muted-foreground">
          {evaluating ? "Evaluating technical accuracy, problem solving, communication, and depth." : "Retrieving your evaluation metrics."}
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-lg py-16 text-center">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-destructive/10 text-destructive">
          <XCircle size={28} />
        </div>
        <h2 className="text-xl font-bold text-foreground">Could not load evaluation</h2>
        <p className="mt-2 text-sm text-muted-foreground">{error}</p>
        <div className="mt-6 flex justify-center gap-3">
          <Button variant="outline" onClick={() => onNavigate("dashboard")}>
            Go to Dashboard
          </Button>
          <Button onClick={() => onNavigate("create-interview")}>
            New Interview
          </Button>
        </div>
      </div>
    );
  }

  if (!interview && !feedback) {
    return (
      <div className="mx-auto max-w-md py-20 text-center">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
          <BrainCircuit size={28} />
        </div>
        <h2 className="text-xl font-bold text-foreground" style={{ fontFamily: "var(--font-display)" }}>
          No Interview Results Yet
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Take your first practice interview to receive detailed AI evaluation and personalized recommendations.
        </p>
        <div className="mt-6">
          <Button onClick={() => onNavigate("create-interview")}>
            <Sparkles size={15} /> Start an Interview
          </Button>
        </div>
      </div>
    );
  }

  const roleTitle = interview?.role || "Technical Interview";
  const modeLabel = interview?.mode === "voice" ? "Voice" : "Text";
  const overallScore = feedback?.overall_score ?? 0;
  const categories = feedback?.category_scores || {
    technical: 0,
    communication: 0,
    problem_solving: 0,
    relevance: 0,
  };

  const radarData = [
    { subject: "Technical", score: categories.technical, fullMark: 100 },
    { subject: "Communication", score: categories.communication, fullMark: 100 },
    { subject: "Problem Solving", score: categories.problem_solving, fullMark: 100 },
    { subject: "Relevance", score: categories.relevance, fullMark: 100 },
    ...(feedback?.topic_analysis?.slice(0, 3).map(t => ({
      subject: t.topic,
      score: t.score,
      fullMark: 100,
    })) || []),
  ];

  const breakdownBars = [
    { label: "Technical Accuracy", score: categories.technical, variant: categories.technical >= 75 ? ("success" as const) : ("default" as const) },
    { label: "Communication", score: categories.communication, variant: categories.communication >= 75 ? ("success" as const) : ("default" as const) },
    { label: "Problem Solving", score: categories.problem_solving, variant: categories.problem_solving >= 75 ? ("success" as const) : ("default" as const) },
    { label: "Answer Relevance", score: categories.relevance, variant: categories.relevance >= 75 ? ("success" as const) : ("default" as const) },
  ];

  const strengthsList = (feedback?.strengths || []).map((s) => {
    const parts = s.split(":");
    return parts.length > 1
      ? { title: parts[0].trim(), desc: parts.slice(1).join(":").trim() }
      : { title: "Strength", desc: s };
  });

  const weaknessesList = (feedback?.weaknesses || []).map((w) => {
    const parts = w.split(":");
    return parts.length > 1
      ? { title: parts[0].trim(), desc: parts.slice(1).join(":").trim() }
      : { title: "Area to Improve", desc: w };
  });

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
              {roleTitle}
            </h1>
            <Badge variant={modeLabel === "Voice" ? "violet" : "default"}>
              {modeLabel === "Voice" ? <Mic size={10} /> : <FileText size={10} />}
              {modeLabel}
            </Badge>
            {interview?.difficulty && (
              <Badge variant="outline">{interview.difficulty}</Badge>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground" style={{ fontFamily: "var(--font-mono)" }}>
            <span className="flex items-center gap-1"><Briefcase size={11} />{interview?.experience_level || "Standard"}</span>
            <span className="flex items-center gap-1"><Clock size={11} />{new Date(feedback?.created_at || Date.now()).toLocaleDateString()}</span>
            {feedback?.question_evaluations && (
              <span>{feedback.question_evaluations.length} questions evaluated</span>
            )}
          </div>
        </div>
        <div className="flex gap-2 shrink-0">
          <Button variant="outline" size="sm" onClick={() => onNavigate("create-interview")}>
            <RotateCcw size={13} /> New Session
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
            <ScoreMeter score={overallScore} />
          </CardContent>
        </Card>

        {/* Radar card */}
        <Card className="sm:col-span-3">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Skill Breakdown</CardTitle>
          </CardHeader>
          <CardContent className="pb-3">
            <SpiderChart data={radarData} dark={dark} />
          </CardContent>
        </Card>
      </div>

      {/* ── Breakdown progress bars ──────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Category Performance</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {breakdownBars.map(({ label, score, variant }) => (
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
          <CardContent className="space-y-3.5">
            {strengthsList.length > 0 ? (
              strengthsList.map(({ title, desc }, idx) => (
                <div key={idx} className="flex gap-3">
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-500">
                    <CheckCircle2 size={11} />
                  </span>
                  <div>
                    <p className="text-sm font-semibold text-foreground">{title}</p>
                    <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{desc}</p>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-muted-foreground">Keep answering questions to identify key strengths.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <XCircle size={15} className="text-amber-500" />
              Areas to Improve
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3.5">
            {weaknessesList.length > 0 ? (
              weaknessesList.map(({ title, desc }, idx) => (
                <div key={idx} className="flex gap-3">
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-amber-500/10 text-amber-500">
                    <XCircle size={11} />
                  </span>
                  <div>
                    <p className="text-sm font-semibold text-foreground">{title}</p>
                    <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{desc}</p>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-muted-foreground">No specific weaknesses flagged.</p>
            )}
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
                Personalized feedback generated by Gemini
              </p>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-5">
          {feedback?.summary && (
            <div className="flex gap-3.5">
              <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                <TrendingUp size={13} />
              </span>
              <div className="min-w-0 flex-1">
                <p className="mb-1 text-sm font-semibold text-foreground" style={{ fontFamily: "var(--font-display)" }}>
                  Overall Assessment
                </p>
                <p className="text-sm leading-relaxed text-muted-foreground">{feedback.summary}</p>
              </div>
            </div>
          )}

          {feedback?.recommendations && feedback.recommendations.length > 0 && (
            <div className="flex gap-3.5">
              <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                <Lightbulb size={13} />
              </span>
              <div className="min-w-0 flex-1">
                <p className="mb-1 text-sm font-semibold text-foreground" style={{ fontFamily: "var(--font-display)" }}>
                  Recommended Action Items
                </p>
                <ul className="space-y-1.5">
                  {feedback.recommendations.map((rec, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                      <ChevronRight size={13} className="mt-0.5 shrink-0 text-primary" />
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Question-by-question breakdown */}
          {feedback?.question_evaluations && feedback.question_evaluations.length > 0 && (
            <div className="pt-2">
              <p className="mb-3 text-sm font-semibold text-foreground" style={{ fontFamily: "var(--font-display)" }}>
                Per-Question Breakdown
              </p>
              <div className="space-y-3">
                {feedback.question_evaluations.map((qe, index) => (
                  <div
                    key={qe.question_id || index}
                    className="rounded-lg border border-border/70 bg-card p-3.5 text-xs text-muted-foreground"
                  >
                    <div className="mb-1.5 flex items-center justify-between">
                      <span className="font-semibold text-foreground" style={{ fontFamily: "var(--font-mono)" }}>
                        Question #{index + 1} ({qe.quality || "Evaluated"})
                      </span>
                      <Badge variant="outline" className="font-bold tabular-nums">
                        {qe.score}/100
                      </Badge>
                    </div>
                    <p className="leading-relaxed">{qe.feedback}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Actions ──────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
        <p className="text-xs text-muted-foreground" style={{ fontFamily: "var(--font-mono)" }}>
          Interview ID: {interview?.id || "N/A"}
        </p>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => onNavigate("dashboard")}>
            Dashboard
          </Button>
          <Button onClick={() => onNavigate("create-interview")}>
            Next Interview <ChevronRight size={14} />
          </Button>
        </div>
      </div>

    </div>
  );
}
