/**
 * src/screens/VoiceInterview.tsx
 *
 * Voice interview screen using the Web Speech API for recording,
 * and the backend's text interview engine for evaluation.
 * Transcribes spoken answers → submits as text to the same engine.
 */

import { useState, useEffect, useRef, useCallback } from "react";
import {
  BrainCircuit,
  Mic,
  MicOff,
  ChevronRight,
  Clock,
  CheckCircle2,
  Loader2,
  RotateCcw,
  Send,
} from "lucide-react";
import { Button } from "../components/ui/button";
import { Progress } from "../components/ui/progress";
import * as interviewApi from "../services/interview.api";
import type { QuestionDoc, SubmitAnswerResponse } from "../services/interview.api";
import type { Screen } from "../types";

interface VoiceInterviewProps {
  onNavigate: (screen: Screen) => void;
  interviewId?: string;
}

type Phase = "loading" | "ready" | "recording" | "submitting" | "evaluating" | "completed" | "error";

declare global {
  interface Window {
    SpeechRecognition: typeof SpeechRecognition;
    webkitSpeechRecognition: typeof SpeechRecognition;
  }
}

function Timer({ startedAt }: { startedAt: number }) {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - startedAt) / 1000)), 1000);
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

export default function VoiceInterview({ onNavigate, interviewId }: VoiceInterviewProps) {
  const [phase, setPhase] = useState<Phase>("loading");
  const [error, setError] = useState<string | null>(null);

  const [currentQuestion, setCurrentQuestion] = useState<QuestionDoc | null>(null);
  const [questionNumber, setQuestionNumber] = useState(1);
  const [totalQuestions, setTotalQuestions] = useState(5);
  const [transcript, setTranscript] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [lastFeedback, setLastFeedback] = useState<SubmitAnswerResponse | null>(null);
  const [showFeedback, setShowFeedback] = useState(false);
  const [finalScore, setFinalScore] = useState<number | null>(null);
  const [questionStartedAt, setQuestionStartedAt] = useState(Date.now());
  const [speechSupported, setSpeechSupported] = useState(true);

  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const activeInterviewId = useRef<string | null>(interviewId ?? null);

  // ── Check speech API support ────────────────────────────────────────
  useEffect(() => {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) setSpeechSupported(false);
  }, []);

  // ── Bootstrap ───────────────────────────────────────────────────────
  const bootstrap = useCallback(async () => {
    setPhase("loading");
    setError(null);
    setShowFeedback(false);
    setTranscript("");

    try {
      const id = activeInterviewId.current;
      if (!id) throw new Error("No interview ID.");

      await interviewApi.generateQuestions(id, 5);
      const startData = await interviewApi.startInterview(id);
      setCurrentQuestion(startData.current_question);
      setQuestionNumber(startData.question_number);
      setTotalQuestions(startData.total_questions);
      setQuestionStartedAt(Date.now());
      setPhase("ready");
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        (err as Error)?.message ?? "Failed to start interview.";
      setError(String(msg));
      setPhase("error");
    }
  }, []);

  useEffect(() => { bootstrap(); }, [bootstrap]);

  // ── Speech recognition ──────────────────────────────────────────────
  function startListening() {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) return;

    const rec = new SpeechRec();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = "en-US";

    rec.onresult = (e) => {
      let final = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        final += e.results[i][0].transcript;
      }
      setTranscript((prev) => prev + (prev ? " " : "") + final);
    };

    rec.onerror = () => setIsListening(false);
    rec.onend = () => setIsListening(false);

    recognitionRef.current = rec;
    rec.start();
    setIsListening(true);
    setPhase("recording");
  }

  function stopListening() {
    recognitionRef.current?.stop();
    setIsListening(false);
    setPhase("ready");
  }

  function toggleListening() {
    if (isListening) stopListening();
    else startListening();
  }

  // ── Submit ──────────────────────────────────────────────────────────
  async function handleSubmit() {
    if (!transcript.trim() || !currentQuestion || !activeInterviewId.current) return;
    if (isListening) stopListening();

    const durationSecs = Math.floor((Date.now() - questionStartedAt) / 1000);
    setPhase("submitting");

    try {
      const feedback = await interviewApi.submitAnswer(
        activeInterviewId.current,
        currentQuestion.id,
        transcript.trim(),
        durationSecs,
      );
      setLastFeedback(feedback);
      setShowFeedback(true);
      setPhase("evaluating");
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to submit.";
      setError(String(msg));
      setPhase("error");
    }
  }

  // ── Next question ───────────────────────────────────────────────────
  async function handleNext() {
    if (!activeInterviewId.current) return;
    setPhase("loading");
    setShowFeedback(false);
    setTranscript("");
    setLastFeedback(null);

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
      setPhase("ready");
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to load next question.";
      setError(String(msg));
      setPhase("error");
    }
  }

  const progress = totalQuestions > 0 ? ((questionNumber - 1) / totalQuestions) * 100 : 0;

  if (phase === "loading") {
    return (
      <div className="flex min-h-[70vh] flex-col items-center justify-center gap-5 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-purple-600/10">
          <Loader2 size={28} className="animate-spin text-purple-500" />
        </div>
        <div>
          <p className="text-lg font-semibold text-foreground" style={{ fontFamily: "var(--font-display)" }}>
            Preparing voice interview…
          </p>
          <p className="mt-1 text-sm text-muted-foreground">AI is generating your questions.</p>
        </div>
      </div>
    );
  }

  if (phase === "error") {
    return (
      <div className="flex min-h-[70vh] flex-col items-center justify-center gap-5 p-8 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/10 text-destructive">
          <Mic size={28} />
        </div>
        <div>
          <h2 className="text-xl font-bold text-foreground" style={{ fontFamily: "var(--font-display)" }}>
            Something went wrong
          </h2>
          <p className="mt-2 max-w-sm text-sm text-muted-foreground leading-relaxed">{error}</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={() => onNavigate("create-interview")}>← New Interview</Button>
          <Button onClick={bootstrap}><RotateCcw size={14} /> Try again</Button>
        </div>
      </div>
    );
  }

  if (phase === "completed") {
    return (
      <div className="flex min-h-[70vh] flex-col items-center justify-center gap-6 p-8 text-center">
        <div className="flex h-20 w-20 items-center justify-center rounded-full bg-purple-600/10 text-purple-500 shadow-[0_0_32px_rgba(168,85,247,0.35)]">
          <CheckCircle2 size={36} />
        </div>
        <div>
          <h2 className="text-3xl font-extrabold tracking-tight text-foreground" style={{ fontFamily: "var(--font-display)" }}>
            Interview Complete!
          </h2>
          <p className="mt-2 text-muted-foreground">You spoke through all {totalQuestions} questions.</p>
          {finalScore !== null && (
            <p className="mt-3 text-5xl font-extrabold tabular-nums text-purple-500" style={{ fontFamily: "var(--font-display)" }}>
              {finalScore}<span className="text-2xl text-muted-foreground">/100</span>
            </p>
          )}
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <Button variant="outline" onClick={() => onNavigate("create-interview")}><RotateCcw size={14} /> New Interview</Button>
          <Button onClick={() => onNavigate("results")}>View Full Results <ChevronRight size={14} /></Button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-5 py-8 pb-12">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-purple-600 to-indigo-600 text-white">
            <Mic size={14} />
          </div>
          <span className="text-sm font-semibold text-foreground" style={{ fontFamily: "var(--font-display)" }}>
            Voice Interview
          </span>
        </div>
        {(phase === "ready" || phase === "recording") && <Timer startedAt={questionStartedAt} />}
      </div>

      {/* Progress */}
      <div className="mb-6 space-y-2">
        <div className="flex items-center justify-between text-xs text-muted-foreground" style={{ fontFamily: "var(--font-mono)" }}>
          <span>Question {questionNumber} of {totalQuestions}</span>
          <span>{Math.round(progress)}% complete</span>
        </div>
        <Progress value={progress} size="sm" />
      </div>

      {/* Question */}
      {currentQuestion && (
        <div className="mb-6 rounded-2xl border border-border bg-card p-6 shadow-sm">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-3" style={{ fontFamily: "var(--font-mono)" }}>
            Q{questionNumber} · {currentQuestion.type?.replace(/_/g, " ") ?? "Question"}
          </p>
          <p className="text-lg font-semibold leading-relaxed text-foreground" style={{ fontFamily: "var(--font-display)" }}>
            {currentQuestion.text}
          </p>
        </div>
      )}

      {/* Feedback */}
      {showFeedback && lastFeedback && (
        <div className="mb-6 rounded-xl border border-purple-500/20 bg-purple-500/[0.04] p-5">
          <div className="flex items-center gap-2 mb-3">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-purple-600 to-indigo-600 text-white">
              <BrainCircuit size={13} />
            </div>
            <p className="text-sm font-semibold text-foreground" style={{ fontFamily: "var(--font-display)" }}>AI Evaluation</p>
            {lastFeedback.score !== undefined && (
              <span className={`ml-auto text-lg font-extrabold tabular-nums ${lastFeedback.score >= 80 ? "text-emerald-500" : lastFeedback.score >= 60 ? "text-amber-500" : "text-red-500"}`} style={{ fontFamily: "var(--font-display)" }}>
                {lastFeedback.score}/100
              </span>
            )}
          </div>
          {lastFeedback.feedback && <p className="text-sm leading-relaxed text-muted-foreground">{lastFeedback.feedback}</p>}
          <div className="mt-4 flex justify-end">
            <Button onClick={handleNext} disabled={phase === "loading"}>
              {questionNumber >= totalQuestions ? <>View Results <CheckCircle2 size={14} /></> : <>Next Question <ChevronRight size={14} /></>}
            </Button>
          </div>
        </div>
      )}

      {/* Recording UI */}
      {!showFeedback && (phase === "ready" || phase === "recording" || phase === "submitting") && (
        <div className="space-y-5">
          {/* Mic button */}
          <div className="flex flex-col items-center gap-4">
            <button
              onClick={toggleListening}
              disabled={phase === "submitting" || !speechSupported}
              className={[
                "relative flex h-24 w-24 items-center justify-center rounded-full transition-all duration-200 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-purple-500/50",
                isListening
                  ? "bg-red-500 text-white shadow-[0_0_40px_rgba(239,68,68,0.5)] scale-110"
                  : "bg-gradient-to-br from-purple-600 to-indigo-600 text-white shadow-[0_0_32px_rgba(168,85,247,0.4)] hover:scale-105",
                phase === "submitting" ? "opacity-50 cursor-not-allowed" : "cursor-pointer",
              ].join(" ")}
              aria-label={isListening ? "Stop recording" : "Start recording"}
            >
              {isListening ? <MicOff size={32} /> : <Mic size={32} />}
              {isListening && (
                <span className="absolute inset-0 animate-ping rounded-full bg-red-500 opacity-25" />
              )}
            </button>
            <p className="text-sm font-medium text-muted-foreground">
              {isListening ? "Recording… click to stop" : "Click to start speaking"}
            </p>
          </div>

          {/* Transcript */}
          <div>
            <p className="mb-1.5 text-xs font-semibold uppercase tracking-widest text-muted-foreground" style={{ fontFamily: "var(--font-mono)" }}>
              Transcript
            </p>
            <div className="min-h-[100px] rounded-xl border border-border bg-input-background p-4 text-sm text-foreground">
              {transcript || (
                <span className="text-muted-foreground">
                  {speechSupported
                    ? "Your spoken words will appear here in real-time…"
                    : "⚠️ Speech recognition is not supported in this browser. Please use Chrome or Edge."}
                </span>
              )}
            </div>
            {transcript && (
              <button
                onClick={() => setTranscript("")}
                className="mt-1.5 text-xs text-muted-foreground hover:text-destructive transition-colors"
              >
                Clear transcript
              </button>
            )}
          </div>

          {/* Submit */}
          <div className="flex justify-end">
            <Button
              onClick={handleSubmit}
              disabled={!transcript.trim() || phase === "submitting"}
            >
              {phase === "submitting" ? (
                <><Loader2 size={14} className="animate-spin" /> Evaluating…</>
              ) : (
                <>Submit Answer <Send size={13} /></>
              )}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
