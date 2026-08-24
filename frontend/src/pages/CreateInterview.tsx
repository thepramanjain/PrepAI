import {
  useState,
  useRef,
  useEffect,
  useCallback,
  type KeyboardEvent,
  type DragEvent,
  type ChangeEvent,
} from "react";
import {
  Keyboard,
  Mic,
  FileUp,
  X,
  Check,
  Sparkles,
  Clock,
  FileText,
  ChevronDown,
  Plus,
} from "lucide-react";
import { Button } from "../components/ui/button";
import { Textarea } from "../components/ui/input";
import { Card, CardContent } from "../components/ui/card";
import type { Screen } from "../types";

// ── Constants ─────────────────────────────────────────────────────────

const EXPERIENCE_OPTIONS = [
  { value: "entry",     label: "Entry Level",       sub: "0 – 2 years" },
  { value: "mid",       label: "Mid Level",          sub: "3 – 5 years" },
  { value: "senior",   label: "Senior",              sub: "6 – 9 years" },
  { value: "staff",    label: "Staff / Principal",   sub: "10+ years" },
];

const DIFFICULTIES = [
  { value: "easy",   label: "Easy",   sub: "Warm-up", dot: "bg-emerald-500", activeCls: "border-emerald-500 bg-emerald-500/10" },
  { value: "medium", label: "Medium", sub: "Standard", dot: "bg-sky-500",    activeCls: "border-sky-500 bg-sky-500/10" },
  { value: "hard",   label: "Hard",   sub: "Stretch",  dot: "bg-amber-500",  activeCls: "border-amber-500 bg-amber-500/10" },
  { value: "expert", label: "Expert", sub: "FAANG+",   dot: "bg-red-500",    activeCls: "border-red-500 bg-red-500/10" },
] as const;

type DifficultyValue = typeof DIFFICULTIES[number]["value"];

const SKILL_SUGGESTIONS = [
  "React", "TypeScript", "Node.js", "Python", "Go", "System Design",
  "AWS", "Kubernetes", "SQL", "GraphQL", "Distributed Systems",
  "Machine Learning", "REST APIs", "Microservices", "CI/CD",
];

const ESTIMATED_TIME: Record<DifficultyValue, string> = {
  easy:   "~15 min",
  medium: "~25 min",
  hard:   "~35 min",
  expert: "~45 min",
};

// ── Prop types ────────────────────────────────────────────────────────

interface CreateInterviewProps {
  onNavigate: (screen: Screen) => void;
}

// ── Tag input ─────────────────────────────────────────────────────────

interface TagInputProps {
  tags: string[];
  onAdd: (tag: string) => void;
  onRemove: (tag: string) => void;
  suggestions: string[];
}

function TagInput({ tags, onAdd, onRemove, suggestions }: TagInputProps) {
  const [value, setValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  function commit() {
    const trimmed = value.trim().replace(/,$/, "");
    if (trimmed && !tags.includes(trimmed) && tags.length < 12) {
      onAdd(trimmed);
    }
    setValue("");
  }

  function handleKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === "Tab" || e.key === ",") {
      e.preventDefault();
      commit();
    } else if (e.key === "Backspace" && !value && tags.length > 0) {
      onRemove(tags[tags.length - 1]);
    }
  }

  const visible = suggestions.filter((s) => !tags.includes(s));

  return (
    <div>
      <div
        className="flex min-h-[44px] cursor-text flex-wrap gap-1.5 rounded-lg border border-border bg-input-background p-2 transition-colors focus-within:border-primary focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-1 focus-within:ring-offset-background"
        onClick={() => inputRef.current?.focus()}
      >
        {tags.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1 rounded-md bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary"
          >
            {tag}
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onRemove(tag); }}
              className="rounded-sm text-primary/60 hover:text-primary focus-visible:outline-none"
              aria-label={`Remove ${tag}`}
            >
              <X size={10} />
            </button>
          </span>
        ))}
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKey}
          onBlur={commit}
          placeholder={tags.length === 0 ? "Type a skill and press Enter…" : ""}
          className="min-w-[160px] flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
        />
      </div>

      {/* Suggestions */}
      {visible.length > 0 && (
        <div className="mt-2.5 flex flex-wrap gap-1.5">
          {visible.slice(0, 10).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => { if (!tags.includes(s) && tags.length < 12) onAdd(s); }}
              className="inline-flex items-center gap-0.5 rounded-md border border-border bg-card px-2 py-0.5 text-xs text-muted-foreground transition-colors hover:border-primary/50 hover:text-primary"
            >
              <Plus size={9} />
              {s}
            </button>
          ))}
        </div>
      )}
      <p className="mt-1.5 text-[11px] text-muted-foreground" style={{ fontFamily: "var(--font-mono)" }}>
        {tags.length}/12 skills · Enter, Tab, or comma to add
      </p>
    </div>
  );
}

// ── Drag-and-drop file upload ─────────────────────────────────────────

interface FileUploadProps {
  file: File | null;
  onSelect: (f: File) => void;
  onClear: () => void;
}

function FileUpload({ file, onSelect, onClear }: FileUploadProps) {
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const accept = (f: File) => {
    setError(null);
    if (f.type !== "application/pdf") {
      setError("Only PDF files are supported.");
      return;
    }
    if (f.size > 10 * 1024 * 1024) {
      setError("File must be under 10 MB.");
      return;
    }
    onSelect(f);
  };

  const onDrop = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) accept(f);
  }, []);

  const onDragOver = (e: DragEvent<HTMLDivElement>) => { e.preventDefault(); setDragging(true); };
  const onDragLeave = () => setDragging(false);
  const onChange = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) accept(f);
  };

  const fmtSize = (bytes: number) => bytes < 1024 * 1024
    ? `${(bytes / 1024).toFixed(0)} KB`
    : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;

  return (
    <div>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,application/pdf"
        className="sr-only"
        onChange={onChange}
      />
      {file ? (
        <div className="flex items-center gap-3 rounded-lg border border-border bg-card p-4">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <FileText size={18} />
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-foreground">{file.name}</p>
            <p className="text-xs text-muted-foreground" style={{ fontFamily: "var(--font-mono)" }}>
              PDF · {fmtSize(file.size)}
            </p>
          </div>
          <button
            type="button"
            onClick={onClear}
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
            aria-label="Remove file"
          >
            <X size={14} />
          </button>
        </div>
      ) : (
        <div
          onDrop={onDrop}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onClick={() => inputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
          aria-label="Upload resume PDF"
          className={[
            "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-center transition-all duration-150",
            dragging
              ? "border-primary bg-primary/5 scale-[1.01]"
              : "border-border bg-transparent hover:border-primary/50 hover:bg-accent/30",
          ].join(" ")}
        >
          <div className={`flex h-11 w-11 items-center justify-center rounded-xl transition-colors ${
            dragging ? "bg-primary/20 text-primary" : "bg-muted text-muted-foreground"
          }`}>
            <FileUp size={20} />
          </div>
          <div>
            <p className="text-sm font-medium text-foreground">
              {dragging ? "Drop to upload" : "Drop your resume here"}
            </p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              or <span className="text-primary underline underline-offset-2">browse files</span> · PDF up to 10 MB
            </p>
          </div>
        </div>
      )}
      {error && (
        <p className="mt-1.5 text-xs text-destructive">{error}</p>
      )}
    </div>
  );
}

// ── Custom experience-level select ───────────────────────────────────

function ExperienceSelect({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleOutside);
    return () => document.removeEventListener("mousedown", handleOutside);
  }, []);

  const selected = EXPERIENCE_OPTIONS.find((o) => o.value === value) ?? EXPERIENCE_OPTIONS[0];

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex h-10 w-full items-center justify-between rounded-lg border border-border bg-input-background px-3 text-sm text-foreground transition-colors hover:border-muted-foreground/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background focus-visible:border-primary"
      >
        <span>
          {selected.label}
          <span className="ml-1.5 text-muted-foreground">({selected.sub})</span>
        </span>
        <ChevronDown
          size={14}
          className={`shrink-0 text-muted-foreground transition-transform duration-150 ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open && (
        <div className="absolute left-0 right-0 top-full z-50 mt-1 overflow-hidden rounded-lg border border-border bg-popover shadow-xl ring-1 ring-black/5 dark:ring-white/[0.06]">
          {EXPERIENCE_OPTIONS.map(({ value: v, label, sub }) => (
            <button
              key={v}
              type="button"
              onClick={() => { onChange(v); setOpen(false); }}
              className={[
                "flex w-full items-center justify-between px-3 py-2.5 text-sm transition-colors",
                "hover:bg-accent hover:text-accent-foreground",
                v === value
                  ? "bg-primary/10 text-primary"
                  : "text-foreground",
              ].join(" ")}
            >
              <span className="font-medium">{label}</span>
              <span className="text-xs text-muted-foreground">{sub}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Form section wrapper ──────────────────────────────────────────────

function Section({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-2.5">
      <div>
        <p className="text-sm font-semibold text-foreground" style={{ fontFamily: "var(--font-display)" }}>
          {label}
        </p>
        {hint && <p className="mt-0.5 text-xs text-muted-foreground">{hint}</p>}
      </div>
      {children}
    </div>
  );
}

// ── Input base classes (mirrors the Input component) ──────────────────

const inputCls =
  "w-full rounded-lg border border-border bg-input-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground transition-colors duration-150 h-10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background focus-visible:border-primary";

// ── Main component ────────────────────────────────────────────────────

export default function CreateInterview({ onNavigate }: CreateInterviewProps) {
  const [role, setRole] = useState("");
  const [experience, setExperience] = useState("mid");
  const [skills, setSkills] = useState<string[]>(["System Design", "TypeScript"]);
  const [difficulty, setDifficulty] = useState<DifficultyValue>("medium");
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState("");
  const [mode, setMode] = useState<"text" | "voice">("text");
  const [submitted, setSubmitted] = useState(false);

  function addSkill(s: string) { setSkills((p) => [...p, s]); }
  function removeSkill(s: string) { setSkills((p) => p.filter((t) => t !== s)); }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitted(true);
    if (!role.trim()) return;
    onNavigate(mode === "voice" ? "voice-interview" : "text-interview");
  }

  const diff = DIFFICULTIES.find((d) => d.value === difficulty)!;

  return (
    <div className="mx-auto max-w-3xl px-5 py-8 pb-12">
      {/* Page header */}
      <div className="mb-8">
        <h1
          className="text-2xl font-bold tracking-tight text-foreground"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Create Interview
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Configure your session and PrepAI will generate a tailored question set.
        </p>
      </div>

      <form onSubmit={handleSubmit} noValidate className="space-y-8">

        {/* ── Row 1: Role + Experience ──────────────────────── */}
        <div className="grid gap-5 sm:grid-cols-2">
          <Section label="Job Role" hint="The title you're interviewing for">
            <div className="relative">
              <input
                type="text"
                value={role}
                onChange={(e) => { setRole(e.target.value); setSubmitted(false); }}
                placeholder="e.g. Senior Software Engineer"
                className={inputCls}
                aria-required
              />
              {submitted && !role.trim() && (
                <p className="mt-1 text-xs text-destructive">Role is required</p>
              )}
            </div>
          </Section>

          <Section label="Experience Level" hint="Calibrates question difficulty">
            <ExperienceSelect value={experience} onChange={setExperience} />
          </Section>
        </div>

        {/* ── Skills ───────────────────────────────────────── */}
        <Section label="Skills" hint="Add the technologies or topics you want to be tested on">
          <TagInput
            tags={skills}
            onAdd={addSkill}
            onRemove={removeSkill}
            suggestions={SKILL_SUGGESTIONS}
          />
        </Section>

        {/* ── Difficulty ───────────────────────────────────── */}
        <Section label="Difficulty" hint="Sets question complexity and expected depth">
          <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
            {DIFFICULTIES.map(({ value, label, sub, dot, activeCls }) => {
              const active = difficulty === value;
              return (
                <button
                  key={value}
                  type="button"
                  role="radio"
                  aria-checked={active}
                  onClick={() => setDifficulty(value)}
                  className={[
                    "relative flex flex-col items-center gap-2 rounded-xl border px-3 py-4 text-center transition-all duration-150",
                    active
                      ? activeCls
                      : "border-border bg-card hover:border-muted-foreground/40 hover:bg-muted/30",
                  ].join(" ")}
                >
                  <span className={`h-2.5 w-2.5 rounded-full ${dot}`} />
                  <span className="text-sm font-semibold text-foreground" style={{ fontFamily: "var(--font-display)" }}>
                    {label}
                  </span>
                  <span className="text-[11px] text-muted-foreground" style={{ fontFamily: "var(--font-mono)" }}>
                    {sub}
                  </span>
                  {active && (
                    <span className="absolute right-2 top-2 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-primary-foreground">
                      <Check size={9} strokeWidth={3} />
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </Section>

        {/* ── Materials: Resume + JD ────────────────────────── */}
        <div className="grid gap-5 sm:grid-cols-2">
          <Section label="Resume" hint="Lets AI tailor questions to your background (optional)">
            <FileUpload
              file={resumeFile}
              onSelect={setResumeFile}
              onClear={() => setResumeFile(null)}
            />
          </Section>

          <Section label="Job Description" hint="Paste the JD to get role-specific questions (optional)">
            <div className="relative">
              <Textarea
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                placeholder="Paste the job description here…"
                className="min-h-[130px] text-sm"
                maxLength={3000}
              />
              <span
                className="absolute bottom-2.5 right-3 text-[10px] text-muted-foreground"
                style={{ fontFamily: "var(--font-mono)" }}
              >
                {jobDescription.length}/3000
              </span>
            </div>
          </Section>
        </div>

        {/* ── Interview Mode ────────────────────────────────── */}
        <Section
          label="Interview Mode"
          hint="Choose how you want to practice answering questions"
        >
          <div className="grid gap-3 sm:grid-cols-2">
            {([
              {
                value: "text" as const,
                icon: Keyboard,
                title: "Text Interview",
                description: "Type your answers at your own pace. Great for technical depth and structured thinking.",
                accentBg: "bg-primary/10",
                accentText: "text-primary",
                selectedCls: "border-primary bg-primary/5",
              },
              {
                value: "voice" as const,
                icon: Mic,
                title: "Voice Interview",
                description: "Speak your answers naturally. Includes delivery coaching, filler word detection, and pace analysis.",
                accentBg: "bg-purple-600/10",
                accentText: "text-purple-600 dark:text-purple-400",
                selectedCls: "border-purple-600 bg-purple-600/5",
              },
            ] as const).map(({ value, icon: Icon, title, description, accentBg, accentText, selectedCls }) => {
              const active = mode === value;
              return (
                <Card
                  key={value}
                  role="radio"
                  aria-checked={active}
                  onClick={() => setMode(value)}
                  tabIndex={0}
                  onKeyDown={(e) => e.key === "Enter" && setMode(value)}
                  className={[
                    "cursor-pointer transition-all duration-150",
                    active
                      ? selectedCls
                      : "border-border hover:border-muted-foreground/50 hover:shadow-sm",
                  ].join(" ")}
                >
                  <CardContent className="flex gap-4 p-5">
                    <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${accentBg} ${accentText} transition-colors`}>
                      <Icon size={22} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <p className="font-semibold text-foreground text-sm" style={{ fontFamily: "var(--font-display)" }}>
                          {title}
                        </p>
                        {active && (
                          <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
                            <Check size={11} strokeWidth={3} />
                          </span>
                        )}
                      </div>
                      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                        {description}
                      </p>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </Section>

        {/* ── Divider ───────────────────────────────────────── */}
        <div className="h-px w-full rounded-full bg-border" />

        {/* ── Submit row ────────────────────────────────────── */}
        <div className="flex flex-col-reverse items-start justify-between gap-3 sm:flex-row sm:items-center">
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <Clock size={12} />
              Estimated length: <span className="font-semibold text-foreground" style={{ fontFamily: "var(--font-mono)" }}>{ESTIMATED_TIME[difficulty]}</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className={`h-2 w-2 rounded-full ${diff.dot}`} />
              {diff.label} · {mode === "voice" ? "Voice" : "Text"} mode
            </span>
          </div>
          <Button type="submit" size="lg" className="w-full sm:w-auto">
            <Sparkles size={15} /> Generate Interview
          </Button>
        </div>

      </form>
    </div>
  );
}
