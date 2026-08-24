import { Plus, ArrowRight, BrainCircuit, Mic, FileText, TrendingUp, Clock, CheckCircle2, AlertTriangle } from "lucide-react";
import { Button } from "../components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Progress } from "../components/ui/progress";
import type { Screen } from "../types";

interface DashboardProps {
  onNavigate: (screen: Screen) => void;
}

const recentSessions = [
  { role: "System Design", company: "Stripe", score: 84, date: "Aug 22", status: "complete" as const },
  { role: "Behavioral — Leadership", company: "Anthropic", score: 91, date: "Aug 21", status: "complete" as const },
  { role: "LC Hard — Graphs", company: "Google", score: 55, date: "Aug 19", status: "needs-work" as const },
  { role: "Product Sense", company: "Figma", score: 77, date: "Aug 18", status: "complete" as const },
];

const readinessTopics = [
  { label: "Behavioral", value: 92, variant: "success" as const },
  { label: "System Design", value: 74, variant: "default" as const },
  { label: "Algorithms & DS", value: 48, variant: "warning" as const },
  { label: "Product Sense", value: 81, variant: "default" as const },
];

export default function Dashboard({ onNavigate }: DashboardProps) {
  return (
    <div className="space-y-8 p-6">
      {/* Header row */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1
            className="text-2xl font-bold text-foreground"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Good morning, Jordan
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            You have a Google onsite in{" "}
            <span className="font-semibold text-foreground">6 days</span>. Let's get ready.
          </p>
        </div>
        <Button onClick={() => onNavigate("create-interview")}>
          <Plus size={15} /> New Interview
        </Button>
      </div>

      {/* KPI strip */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { icon: CheckCircle2, label: "Sessions this week", value: "12", color: "text-emerald-500" },
          { icon: TrendingUp, label: "Avg. score", value: "78 / 100", color: "text-primary" },
          { icon: Clock, label: "Hours practiced", value: "8.4 h", color: "text-violet-500" },
          { icon: AlertTriangle, label: "Weak topics", value: "2 topics", color: "text-amber-500" },
        ].map(({ icon: Icon, label, value, color }) => (
          <Card key={label}>
            <CardContent className="flex items-center gap-4 p-5">
              <div className={`${color} shrink-0`}>
                <Icon size={22} />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">{label}</p>
                <p
                  className="mt-0.5 text-xl font-bold text-foreground"
                  style={{ fontFamily: "var(--font-display)" }}
                >
                  {value}
                </p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Quick start */}
        <div className="space-y-3 lg:col-span-1">
          <h2
            className="text-sm font-semibold text-foreground"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Quick Start
          </h2>
          {[
            { icon: FileText, label: "Text Interview", sub: "Type-based Q&A", screen: "text-interview" as Screen, accent: "bg-primary/10 text-primary" },
            { icon: Mic, label: "Voice Interview", sub: "Spoken responses", screen: "voice-interview" as Screen, accent: "bg-violet-500/10 text-violet-500" },
            { icon: BrainCircuit, label: "Custom Session", sub: "Pick your own topics", screen: "create-interview" as Screen, accent: "bg-amber-500/10 text-amber-500" },
          ].map(({ icon: Icon, label, sub, screen, accent }) => (
            <button
              key={label}
              onClick={() => onNavigate(screen)}
              className="flex w-full items-center gap-4 rounded-lg border border-border bg-card p-4 text-left transition-all duration-150 hover:border-primary/40 hover:shadow-sm active:scale-[0.99]"
            >
              <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${accent}`}>
                <Icon size={18} />
              </div>
              <div>
                <p className="font-medium text-foreground text-sm">{label}</p>
                <p className="text-xs text-muted-foreground">{sub}</p>
              </div>
              <ArrowRight size={14} className="ml-auto text-muted-foreground" />
            </button>
          ))}
        </div>

        {/* Readiness scores */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Readiness by Topic</CardTitle>
            <CardDescription>Based on your last 20 sessions</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            {readinessTopics.map(({ label, value, variant }) => (
              <Progress key={label} label={label} value={value} showLabel variant={variant} size="md" />
            ))}
          </CardContent>
          <CardFooter>
            <Button variant="ghost" size="sm" onClick={() => onNavigate("analytics")}>
              Full analytics <ArrowRight size={13} />
            </Button>
          </CardFooter>
        </Card>
      </div>

      {/* Recent sessions */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <h2
            className="text-sm font-semibold text-foreground"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Recent Sessions
          </h2>
          <Button variant="ghost" size="sm" onClick={() => onNavigate("results")}>
            View all <ArrowRight size={13} />
          </Button>
        </div>
        <Card>
          <div className="divide-y divide-border">
            {recentSessions.map(({ role, company, score, date, status }) => (
              <div
                key={`${role}-${date}`}
                className="flex items-center gap-4 px-5 py-4 transition-colors hover:bg-muted/40"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-foreground truncate">{role}</p>
                  <p
                    className="text-xs text-muted-foreground"
                    style={{ fontFamily: "var(--font-mono)" }}
                  >
                    {company} · {date}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span
                    className="text-base font-bold tabular-nums text-foreground"
                    style={{ fontFamily: "var(--font-mono)" }}
                  >
                    {score}
                    <span className="text-xs font-normal text-muted-foreground">/100</span>
                  </span>
                  <Badge variant={status === "complete" ? "success" : "warning"}>
                    {status === "complete" ? "Passed" : "Needs Work"}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
