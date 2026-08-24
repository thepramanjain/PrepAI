import { FileText, Mic, BarChart3, PlusCircle, Trophy } from "lucide-react";
import type { Screen } from "../types";

interface PlaceholderProps {
  onNavigate?: (screen: Screen) => void;
}

function PlaceholderScreen({
  icon: Icon,
  title,
  description,
  accentClass,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
  accentClass: string;
}) {
  return (
    <div className="flex h-full min-h-[60vh] flex-col items-center justify-center gap-5 p-8 text-center">
      <div className={`flex h-16 w-16 items-center justify-center rounded-2xl ${accentClass}`}>
        <Icon size={28} />
      </div>
      <div>
        <h2
          className="text-2xl font-bold text-foreground"
          style={{ fontFamily: "var(--font-display)" }}
        >
          {title}
        </h2>
        <p className="mt-2 max-w-sm text-sm text-muted-foreground leading-relaxed">{description}</p>
      </div>
      <div className="h-px w-20 rounded-full bg-border" />
      <p
        className="text-xs text-muted-foreground"
        style={{ fontFamily: "var(--font-mono)" }}
      >
        screen in development
      </p>
    </div>
  );
}

export function CreateInterview(_: PlaceholderProps) {
  return (
    <PlaceholderScreen
      icon={PlusCircle}
      title="Create Interview"
      description="Configure your session — pick role, company, topics, and difficulty. The AI builds a tailored question set."
      accentClass="bg-amber-500/10 text-amber-500"
    />
  );
}

export function TextInterview(_: PlaceholderProps) {
  return (
    <PlaceholderScreen
      icon={FileText}
      title="Text Interview"
      description="Type your answers at your own pace. AI scores each response on clarity, structure, and technical depth."
      accentClass="bg-primary/10 text-primary"
    />
  );
}

export function VoiceInterview(_: PlaceholderProps) {
  return (
    <PlaceholderScreen
      icon={Mic}
      title="Voice Interview"
      description="Speak your answers naturally. Real-time transcription, filler word detection, and delivery coaching included."
      accentClass="bg-gradient-to-br from-purple-600/20 to-indigo-600/20 text-purple-500 shadow-[0_0_24px_rgba(168,85,247,0.35)] dark:shadow-[0_0_32px_rgba(168,85,247,0.5)]"
    />
  );
}

export function Results(_: PlaceholderProps) {
  return (
    <PlaceholderScreen
      icon={Trophy}
      title="Results & History"
      description="Browse past sessions, compare scores over time, and drill into question-by-question breakdowns."
      accentClass="bg-emerald-500/10 text-emerald-500"
    />
  );
}

export function Analytics(_: PlaceholderProps) {
  return (
    <PlaceholderScreen
      icon={BarChart3}
      title="Analytics"
      description="Readiness trends, topic heatmaps, improvement velocity, and predicted offer probability — all in one view."
      accentClass="bg-indigo-600/10 text-indigo-600 dark:text-indigo-400"
    />
  );
}
