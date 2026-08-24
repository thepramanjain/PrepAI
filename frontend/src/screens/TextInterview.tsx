/**
 * src/screens/TextInterview.tsx
 *
 * Functional text interview screen.
 * Flow:
 *  1. createInterview()  → interview document
 *  2. generateQuestions() → AI generates questions via Gemini
 *  3. startInterview()   → returns first question
 *  4. User types answer → submitAnswer() → nextQuestion()
 *  5. If completed → navigate to "results"
 */

import { useState, useEffect, useRef, useCallback } from "react";
import {
  BrainCircuit,
  Send,
  ChevronRight,
  Clock,
  CheckCircle2,
  Loader2,
  RotateCcw,
  FileText,
} from "lucide-react";
import { Button } from "../components/ui/button";
import { Progress } from "../components/ui/progress";
import * as interviewApi from "../services/interview.api";
import type {
  QuestionDoc,
  SubmitAnswerResponse,
} from "../services/interview.api";
import type { Screen } from "../types";

interface TextInterviewProps {
  onNavigate: (screen: Screen) => void;
  interviewId?: string;
}

type Phase = "loading" | "ready" | "submitting" | "evaluating" | "completed" | "error";

function Timer({ startedAt }: { startedAt: number }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);
    return () => clearInterval(id);
  }, [startedAt]);

  const m = Math.floor(elapsed / 60).toString().padStart(2, "0");
  const s = (elapsed % 60).toString().padStart(2, "0");

  return (
    <span className="flex items-center gap-1 text-xs text-muted-foreground" style={{ fontFamily: "var(--font-mono)" }}>
      <Clock size={11} /> {m}:{s}
    </span>
  );
}

export default function TextInterview({ onNavigate, interviewId }: TextInterviewProps) {
  const [phase, setPhase] = useState<Phase>("loading");
  const [error, setError] = useState<string | null>(null);

  // Interview state
  const [currentQuestion, setCurrentQuestion] = useState<QuestionDoc | null>(null);
  const [questionNumber, setQuestionNumber] = useState(1);
  const [totalQuestions, setTotalQuestions] = useState(5);
  const [answer, setAnswer] = useState("");
  const [lastFeedback, setLastFeedback] = useState<SubmitAnswerResponse | null>(null);
  const [showFeedback, setShowFeedback] = useState(false);
  const [finalScore, setFinalScore] = useState<number | null>(null);
  const [questionStartedAt, setQuestionStartedAt] = useState(Date.now());

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const activeInterviewId = useRef<string | null>(interviewId ?? null);

  // ── Bootstrap: start the interview ─────────────────────────────────
  const bootstrap = useCallback(async () => {
    setPhase("loading");
    setError(null);
    setShowFeedback(false);
    setLastFeedback(null);

    try {
      const id = activeInterviewId.current;
      if (!id) throw new Error("No interview ID. Please create an interview first.");

      // Generate AI questions first
      await interviewApi.generateQuestions(id, 5);

      // Start the interview engine
      const startData = await interviewApi.startInterview(id);
      setCurrentQuestion(startData.current_question);
      setQuestionNumber(startData.question_number);
      setTotalQuestions(startData.total_questions);
      setQuestionStartedAt(Date.now());
      setPhase("ready");
      setTimeout(() => textareaRef.current?.focus(), 100);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        (err as Error)?.message ??
        "Failed to start interview.";
      setError(String(msg));
      setPhase("error");
    }
  }, []);

  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  // ── Submit an answer ────────────────────────────────────────────────
  async function handleSubmit() {
    if (!answer.trim() || !currentQuestion || !activeInterviewId.current) return;

    const durationSecs = Math.floor((Date.now() - questionStartedAt) / 1000);
    setPhase("submitting");

    try {
      const feedback = await interviewApi.submitAnswer(
        activeInterviewId.current,
        currentQuestion.id,
        answer.trim(),
        durationSecs,
      );
      setLastFeedback(feedback);
      setShowFeedback(true);
      setPhase("evaluating");
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to submit answer.";
      setError(String(msg));
      setPhase("error");
    }
  }

  // ── Move to next question ────────────────────────────────────────────
  async function handleNext() {
    if (!activeInterviewId.current) return;
    setPhase("loading");
    setShowFeedback(false);
    setAnswer("");

    try {
      const next = await interviewApi.nextQuestion(activeInterviewId.current);

      if (next.completed) {
        setFinalScore(next.final_score ?? null);
        setPhase("completed");
        return;
      }

      if (next.current_question) {
        setCurrentQuestion(next.current_question);
        setQuestionNumber(next.question_number ?? questionNumber + 1);
        setTotalQuestions(next.total_questions ?? totalQuestions);
        setQuestionStartedAt(Date.now());
      }

      setLastFeedback(null);
      setPhase("ready");
      setTimeout(() => textareaRef.current?.focus(), 100);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to load next question.";
      setError(String(msg));
      setPhase("error");
    }
  }

  const progress = totalQuestions > 0 ? ((questionNumber - 1) / totalQuestions) * 100 : 0;

  // ── Loading state ────────────────────────────────────────────────────
  if (phase === "loading") {
    return (
      <div className="flex min-h-[70vh] flex-col items-center justify-center gap-5 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
          <Loader2 size={28} className="animate-spin text-primary" />
        </div>
        <div>
          <p className="text-lg font-semibold text-foreground" style={{ fontFamily: "var(--font-display)" }}>
            {questionNumber === 1 ? "Generating your interview…" : "Loading next question…"}
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            PrepAI is tailoring questions to your profile.
          </p>
        </div>
      </div>
    );
  }

  // ── Error state ──────────────────────────────────────────────────────
  if (phase === "error") {
    return (
      <div className="flex min-h-[70vh] flex-col items-center justify-center gap-5 p-8 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/10 text-destructive">
          <FileText size={28} />
        </div>
        <div>
          <h2 className="text-xl font-bold text-foreground" style={{ fontFamily: "var(--font-display)" }}>
            Something went wrong
          </h2>
          <p className="mt-2 max-w-sm text-sm text-muted-foreground leading-relaxed">{error}</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={() => onNavigate("create-interview")}>
            ← New Interview
          </Button>
          <Button onClick={bootstrap}>
            <RotateCcw size={14} /> Try again
          </Button>
        </div>
      </div>
    );
  }

  // ── Completed state ──────────────────────────────────────────────────
  if (phase === "completed") {
    return (
      <div className="flex min-h-[70vh] flex-col items-center justify-center gap-6 p-8 text-center">
        <div className="flex h-20 w-20 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-500 shadow-[0_0_32px_rgba(16,185,129,0.25)]">
          <CheckCircle2 size={36} />
        </div>
        <div>
          <h2
            className="text-3xl font-extrabold tracking-tight text-foreground"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Interview Complete!
          </h2>
          <p className="mt-2 text-muted-foreground">
            You answered all {totalQuestions} questions.
          </p>
          {finalScore !== null && (
            <p className="mt-3 text-5xl font-extrabold tabular-nums text-emerald-500" style={{ fontFamily: "var(--font-display)" }}>
              {finalScore}<span className="text-2xl text-muted-foreground">/100</span>
            </p>
          )}
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <Button variant="outline" onClick={() => onNavigate("create-interview")}>
            <RotateCcw size={14} /> New Interview
          </Button>
          <Button onClick={() => onNavigate("results")}>
            View Full Results <ChevronRight size={14} />
          </Button>
        </div>
      </div>
    );
  }

  // ── Main interview UI ────────────────────────────────────────────────
  return (
    <div className="mx-auto max-w-3xl px-5 py-8 pb-12">

      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <BrainCircuit size={14} />
          </div>
          <span
            className="text-sm font-semibold text-foreground"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Text Interview
          </span>
        </div>
        {phase === "ready" && <Timer startedAt={questionStartedAt} />}
      </div>

      {/* Progress */}
      <div className="mb-6 space-y-2">
        <div className="flex items-center justify-between text-xs text-muted-foreground" style={{ fontFamily: "var(--font-mono)" }}>
          <span>Question {questionNumber} of {totalQuestions}</span>
          <span>{Math.round(progress)}% complete</span>
        </div>
        <Progress value={progress} size="sm" />
      </div>

      {/* Question card */}
      {currentQuestion && (
        <div className="mb-6 rounded-2xl border border-border bg-card p-6 shadow-sm">
          <p
            className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-3"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            Q{questionNumber} · {currentQuestion.type?.replace(/_/g, " ") ?? "Interview Question"}
          </p>
          <p
            className="text-lg font-semibold leading-relaxed text-foreground"
            style={{ fontFamily: "var(--font-display)" }}
          >
            {currentQuestion.text}
          </p>
        </div>
      )}

      {/* AI Feedback panel */}
      {showFeedback && lastFeedback && (
        <div className="mb-6 rounded-xl border border-primary/20 bg-primary/[0.04] p-5">
          <div className="flex items-center gap-2 mb-3">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <BrainCircuit size={13} />
            </div>
            <p className="text-sm font-semibold text-foreground" style={{ fontFamily: "var(--font-display)" }}>
              AI Evaluation
            </p>
            {lastFeedback.score !== undefined && (
              <span
                className={`ml-auto text-lg font-extrabold tabular-nums ${
                  lastFeedback.score >= 80 ? "text-emerald-500" :
                  lastFeedback.score >= 60 ? "text-amber-500" : "text-red-500"
                }`}
                style={{ fontFamily: "var(--font-display)" }}
              >
                {lastFeedback.score}/100
              </span>
            )}
          </div>
          {lastFeedback.feedback && (
            <p className="text-sm leading-relaxed text-muted-foreground">{lastFeedback.feedback}</p>
          )}
          <div className="mt-4 flex justify-end">
            <Button onClick={handleNext} disabled={phase === "loading"}>
              {questionNumber >= totalQuestions ? (
                <>View Results <CheckCircle2 size={14} /></>
              ) : (
                <>Next Question <ChevronRight size={14} /></>
              )}
            </Button>
          </div>
        </div>
      )}

      {/* Answer textarea */}
      {!showFeedback && (phase === "ready" || phase === "submitting") && (
        <div className="space-y-4">
          <div className="relative">
            <textarea
              ref={textareaRef}
              id="answer-textarea"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                  e.preventDefault();
                  handleSubmit();
                }
              }}
              placeholder="Type your answer here… (Ctrl+Enter to submit)"
              disabled={phase === "submitting"}
              rows={8}
              className="w-full rounded-xl border border-border bg-input-background px-4 py-3.5 text-sm text-foreground placeholder:text-muted-foreground transition-colors duration-150 resize-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background focus-visible:border-primary disabled:opacity-60"
            />
            <span
              className="absolute bottom-3 right-3 text-[10px] text-muted-foreground"
              style={{ fontFamily: "var(--font-mono)" }}
            >
              {answer.length} chars
            </span>
          </div>

          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground" style={{ fontFamily: "var(--font-mono)" }}>
              Press{" "}
              <kbd className="rounded border border-border bg-muted px-1 py-0.5 text-[10px]">Ctrl+↵</kbd>{" "}
              to submit
            </p>
            <Button
              id="submit-answer"
              onClick={handleSubmit}
              disabled={!answer.trim() || phase === "submitting"}
            >
              {phase === "submitting" ? (
                <>
                  <Loader2 size={14} className="animate-spin" /> Submitting…
                </>
              ) : (
                <>
                  Submit Answer <Send size={13} />
                </>
              )}
            </Button>
          </div>
        </div>
      )}

      {/* Evaluating state */}
      {phase === "evaluating" && !showFeedback && (
        <div className="flex items-center justify-center gap-3 py-12">
          <Loader2 size={20} className="animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">AI is evaluating your answer…</p>
        </div>
      )}

    </div>
  );
}
