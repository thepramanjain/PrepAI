import { ArrowRight, BrainCircuit, Mic, BarChart3, CheckCircle2, Sparkles, Shield, Zap } from "lucide-react";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Card, CardContent } from "../components/ui/card";
import type { Screen } from "../types";

interface LandingProps {
  onNavigate: (screen: Screen) => void;
}

const features = [
  {
    icon: BrainCircuit,
    title: "AI-Powered Feedback",
    desc: "Real-time analysis of your answers using advanced language models tuned for technical and behavioral interviews.",
  },
  {
    icon: Mic,
    title: "Voice Interview Mode",
    desc: "Practice spoken answers with automatic transcription and delivery coaching — tone, pace, and filler words included.",
  },
  {
    icon: BarChart3,
    title: "Performance Analytics",
    desc: "Track readiness scores by topic, identify weak spots, and watch your improvement over time with clear charts.",
  },
  {
    icon: Shield,
    title: "Role-Specific Prep",
    desc: "Tailored question banks for Engineering, PM, Design, and Data roles at FAANG, startups, and beyond.",
  },
  {
    icon: Zap,
    title: "Instant Scoring",
    desc: "Every response scored across clarity, structure, and technical depth within seconds — no waiting, no fluff.",
  },
  {
    icon: CheckCircle2,
    title: "STAR Method Coaching",
    desc: "Guided frameworks for behavioral questions so your stories land with precision and confidence every time.",
  },
];

const stats = [
  { value: "92%", label: "of users land offers faster" },
  { value: "4.8×", label: "more practice than solo prep" },
  { value: "150+", label: "company-specific tracks" },
  { value: "2M+", label: "questions answered" },
];

export default function Landing({ onNavigate }: LandingProps) {
  return (
    <div className="min-h-screen bg-background">
      <section className="relative mx-auto max-w-5xl px-6 pb-24 pt-20 text-center">
        <h1
          className="mx-auto max-w-4xl text-6xl font-extrabold leading-tight tracking-tight text-foreground sm:text-7xl"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Ace every interview. <span className="text-primary">Every time.</span>
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
          PrepAI coaches you through technical and behavioral interviews
          <br className="hidden sm:block" />
          with real-time AI feedback, voice analysis, and role-specific
          <br className="hidden sm:block" />
          question banks.
        </p>
        <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
          <Button size="lg" className="px-8 text-base" onClick={() => onNavigate("dashboard")}>
            Start Practicing Free <ArrowRight size={16} className="ml-1" />
          </Button>
          <Button size="lg" variant="outline" className="px-8 text-base border-muted-foreground/30 text-foreground" onClick={() => onNavigate("create-interview")}>
            Explore Interview Types
          </Button>
        </div>
      </section>

      {/* Stats bar */}
      <section className="border-y border-border bg-card">
        <div className="mx-auto grid max-w-5xl grid-cols-2 divide-x divide-border px-6 sm:grid-cols-4">
          {stats.map(({ value, label }) => (
            <div key={label} className="py-8 text-center">
              <p
                className="text-3xl font-bold text-foreground"
                style={{ fontFamily: "var(--font-display)" }}
              >
                {value}
              </p>
              <p className="mt-1 text-sm text-muted-foreground">{label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features grid */}
      <section className="mx-auto max-w-5xl px-6 py-20">
        <div className="mb-12 text-center">
          <h2
            className="text-3xl font-bold tracking-tight text-foreground"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Everything you need to land the role
          </h2>
          <p className="mt-3 text-muted-foreground">
            A complete system, not just a question bank.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {features.map(({ icon: Icon, title, desc }) => (
            <Card key={title} className="group transition-shadow duration-200 hover:shadow-md">
              <CardContent className="p-6">
                <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                  <Icon size={18} />
                </div>
                <h3
                  className="mb-1.5 font-semibold text-foreground"
                  style={{ fontFamily: "var(--font-display)" }}
                >
                  {title}
                </h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{desc}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* CTA banner */}
      <section className="mx-auto max-w-5xl px-6 pb-20">
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-violet-700 via-purple-700 to-indigo-700 px-8 py-12 text-center text-white">
          <h2
            className="mb-3 text-3xl font-bold"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Ready to start practicing?
          </h2>
          <p className="mb-8 text-white/80">
            Join 50,000+ candidates who prep smarter with PrepAI.
          </p>
          <Button
            size="lg"
            className="bg-white text-violet-700 hover:bg-white/90 font-semibold shadow-lg"
            onClick={() => onNavigate("dashboard")}
          >
            Get started — it's free <ArrowRight size={16} />
          </Button>
          <div
            aria-hidden
            className="pointer-events-none absolute -right-16 -top-16 h-64 w-64 rounded-full bg-white/5"
          />
          <div
            aria-hidden
            className="pointer-events-none absolute -bottom-20 -left-20 h-72 w-72 rounded-full bg-white/5"
          />
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-8 text-center">
        <p className="text-xs text-muted-foreground">
          © {new Date().getFullYear()} PrepAI. All rights reserved.
        </p>
        <p className="mt-1.5 text-xs text-zinc-500">
          Made with ❤️ by Praman Jain &amp; Prince Saxena
        </p>
      </footer>
    </div>
  );
}
