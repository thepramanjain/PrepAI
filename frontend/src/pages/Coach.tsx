import { useState, useRef, useEffect } from "react";
import {
  Sparkles,
  Send,
  User,
  Bot,
  Target,
  CheckCircle2,
  AlertTriangle,
  Lightbulb,
  ArrowRight,
  Loader2,
  RefreshCw,
  Compass,
  TrendingUp,
} from "lucide-react";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import type { Screen } from "../types";
import { runAgent, type AgentResponse, type CoachingResult } from "../services/agent.api";

interface CoachProps {
  onNavigate: (screen: Screen, state?: Record<string, any>) => void;
  dark?: boolean;
}

interface ChatMessage {
  id: string;
  sender: "user" | "agent";
  text: string;
  task?: string;
  coachingData?: CoachingResult;
  timestamp: Date;
}

const SUGGESTED_PROMPTS = [
  {
    title: "Diagnose Weaknesses",
    prompt: "What are my biggest weaknesses across my past mock interviews?",
    icon: AlertTriangle,
  },
  {
    title: "Action Plan",
    prompt: "Analyze my recent interview performance and build me a prioritized preparation plan.",
    icon: Target,
  },
  {
    title: "Next Study Focus",
    prompt: "What specific technical and behavioral topics should I focus on next?",
    icon: Lightbulb,
  },
  {
    title: "Performance Trends",
    prompt: "Am I improving over time? How are my category scores trending?",
    icon: TrendingUp,
  },
];

export default function Coach({ onNavigate }: CoachProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      sender: "agent",
      text: "Hello! I'm your PrepAI Career Coach. I reason across your interview scores, answer transcripts, and performance history to provide targeted coaching and actionable study plans. How can I help you today?",
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleSend = async (textToSend?: string) => {
    const query = (textToSend || inputValue).trim();
    if (!query || isLoading) return;

    setError(null);
    setInputValue("");

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: "user",
      text: query,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const result: AgentResponse = await runAgent(query);
      const agentMsg: ChatMessage = {
        id: `agent-${Date.now()}`,
        sender: "agent",
        text: result.response || "I have analyzed your request.",
        task: result.task,
        coachingData: result.data?.coaching,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, agentMsg]);
    } catch (err: any) {
      console.error("Agent error:", err);
      const errDetail =
        err?.response?.data?.detail || "Could not reach the AI Coach. Please make sure you are logged in and try again.";
      setError(errDetail);
      const errorMsg: ChatMessage = {
        id: `agent-error-${Date.now()}`,
        sender: "agent",
        text: `Sorry, I encountered an issue: ${errDetail}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const getPriorityBadge = (priority: string) => {
    switch (priority?.toLowerCase()) {
      case "high":
        return <Badge variant="destructive" className="uppercase text-[10px]">High Priority</Badge>;
      case "medium":
        return <Badge variant="warning" className="uppercase text-[10px]">Medium Priority</Badge>;
      default:
        return <Badge variant="success" className="uppercase text-[10px]">Low Priority</Badge>;
    }
  };

  return (
    <div className="flex h-full flex-col bg-background">
      {/* Top Banner / Header */}
      <div className="shrink-0 border-b border-border bg-card/60 px-6 py-4 backdrop-blur-sm">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-md">
              <Sparkles size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold tracking-tight text-foreground" style={{ fontFamily: "var(--font-display)" }}>
                  AI Career Coach & Agent
                </h1>
                <Badge variant="outline" className="border-indigo-500/30 bg-indigo-500/10 text-[10px] text-indigo-500">
                  GPT-4o Agent
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                Autonomous interview intelligence, weakness diagnosis, and personalized career roadmaps.
              </p>
            </div>
          </div>
          <div className="mt-2 flex items-center gap-2 sm:mt-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onNavigate("create-interview")}
              className="text-xs"
            >
              Start Practice Session
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onNavigate("analytics")}
              className="text-xs"
            >
              View Analytics
            </Button>
          </div>
        </div>
      </div>

      {/* Main Conversation Stream */}
      <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-8">
        <div className="mx-auto flex max-w-4xl flex-col gap-6">
          {/* Quick Prompts on initial screen */}
          {messages.length <= 1 && (
            <div className="mb-2">
              <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground" style={{ fontFamily: "var(--font-mono)" }}>
                Suggested Inquiries
              </p>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {SUGGESTED_PROMPTS.map((sp, idx) => {
                  const Icon = sp.icon;
                  return (
                    <button
                      key={idx}
                      onClick={() => handleSend(sp.prompt)}
                      className="group flex items-start gap-3 rounded-xl border border-border bg-card p-3.5 text-left transition-all hover:border-primary/50 hover:bg-accent/50 hover:shadow-sm"
                    >
                      <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                        <Icon size={15} />
                      </div>
                      <div className="flex-1">
                        <p className="text-xs font-semibold text-foreground group-hover:text-primary transition-colors">
                          {sp.title}
                        </p>
                        <p className="mt-0.5 text-xs text-muted-foreground line-clamp-2">
                          {sp.prompt}
                        </p>
                      </div>
                      <ArrowRight size={13} className="shrink-0 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Message List */}
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3.5 ${msg.sender === "user" ? "justify-end" : "justify-start"}`}
            >
              {msg.sender === "agent" && (
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary border border-primary/20">
                  <Bot size={16} />
                </div>
              )}

              <div
                className={`flex max-w-[85%] flex-col gap-2 rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  msg.sender === "user"
                    ? "bg-primary text-primary-foreground shadow-sm rounded-br-none"
                    : "bg-card border border-border text-foreground shadow-xs rounded-bl-none"
                }`}
              >
                {/* Message Text */}
                <div className="whitespace-pre-wrap">{msg.text}</div>

                {/* Structured Coaching Plan Card (if returned by agent) */}
                {msg.coachingData && (
                  <div className="mt-3 flex flex-col gap-3 rounded-xl border border-border/80 bg-accent/40 p-4 text-card-foreground">
                    {/* Summary */}
                    {msg.coachingData.summary && (
                      <div className="rounded-lg bg-background/80 p-3 text-xs leading-relaxed border border-border/50">
                        <span className="font-semibold text-primary">Assessment: </span>
                        {msg.coachingData.summary}
                      </div>
                    )}

                    {/* Strengths & Focus Tags */}
                    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                      {msg.coachingData.strengths && msg.coachingData.strengths.length > 0 && (
                        <div className="flex flex-col gap-1.5">
                          <span className="text-[11px] font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                            <CheckCircle2 size={12} /> Key Strengths
                          </span>
                          <div className="flex flex-wrap gap-1">
                            {msg.coachingData.strengths.map((str, i) => (
                              <Badge key={i} variant="outline" className="border-emerald-500/20 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 text-[11px]">
                                {str}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}

                      {msg.coachingData.priority_weaknesses && msg.coachingData.priority_weaknesses.length > 0 && (
                        <div className="flex flex-col gap-1.5">
                          <span className="text-[11px] font-semibold uppercase tracking-wider text-amber-600 dark:text-amber-400 flex items-center gap-1">
                            <AlertTriangle size={12} /> Priority Weaknesses
                          </span>
                          <div className="flex flex-wrap gap-1">
                            {msg.coachingData.priority_weaknesses.map((w, i) => (
                              <Badge key={i} variant="outline" className="border-amber-500/20 bg-amber-500/10 text-amber-700 dark:text-amber-300 text-[11px]">
                                {w}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Focus Topics */}
                    {msg.coachingData.focus_topics && msg.coachingData.focus_topics.length > 0 && (
                      <div className="flex flex-col gap-1.5 pt-1">
                        <span className="text-[11px] font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 flex items-center gap-1">
                          <Lightbulb size={12} /> Recommended Study Topics
                        </span>
                        <div className="flex flex-wrap gap-1">
                          {msg.coachingData.focus_topics.map((top, i) => (
                            <Badge key={i} variant="outline" className="border-indigo-500/20 bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 text-[11px]">
                              {top}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Action Plan */}
                    {msg.coachingData.action_plan && msg.coachingData.action_plan.length > 0 && (
                      <div className="flex flex-col gap-2 pt-2 border-t border-border/60">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-foreground flex items-center gap-1.5">
                          <Compass size={13} /> Action Plan Checklist
                        </span>
                        <div className="flex flex-col gap-2">
                          {msg.coachingData.action_plan.map((item, idx) => (
                            <div
                              key={idx}
                              className="flex flex-col gap-1 rounded-lg border border-border/50 bg-background/90 p-2.5 text-xs shadow-2xs"
                            >
                              <div className="flex items-center justify-between gap-2">
                                <span className="font-semibold text-foreground flex items-center gap-1.5">
                                  <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-primary/20 text-[10px] text-primary font-bold">
                                    {idx + 1}
                                  </span>
                                  {item.task}
                                </span>
                                {getPriorityBadge(item.priority)}
                              </div>
                              <p className="text-muted-foreground pl-5.5 text-[11px]">
                                {item.reason}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Timestamp */}
                <span
                  className={`text-[10px] self-end mt-0.5 ${
                    msg.sender === "user" ? "text-primary-foreground/70" : "text-muted-foreground"
                  }`}
                >
                  {msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
              </div>

              {msg.sender === "user" && (
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">
                  <User size={15} />
                </div>
              )}
            </div>
          ))}

          {/* Typing Indicator */}
          {isLoading && (
            <div className="flex gap-3.5 justify-start">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary border border-primary/20">
                <Bot size={16} />
              </div>
              <div className="flex items-center gap-2 rounded-2xl rounded-bl-none border border-border bg-card px-4 py-3 text-sm text-muted-foreground">
                <Loader2 size={16} className="animate-spin text-primary" />
                <span>Coach is thinking, querying your records, and formulating insights…</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="shrink-0 border-t border-border bg-card p-4 sm:p-5">
        <div className="mx-auto max-w-4xl">
          {error && (
            <div className="mb-2 flex items-center justify-between rounded-lg bg-destructive/10 px-3 py-1.5 text-xs text-destructive">
              <span>{error}</span>
              <Button variant="ghost" size="sm" onClick={() => setError(null)} className="h-6 px-1.5 text-xs">
                Dismiss
              </Button>
            </div>
          )}
          <div className="flex items-end gap-2 rounded-xl border border-border bg-background p-2 shadow-2xs focus-within:border-primary focus-within:ring-1 focus-within:ring-primary">
            <textarea
              rows={1}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask your Career Coach anything (e.g., 'What are my weak spots?' or 'Build my study plan')..."
              disabled={isLoading}
              className="flex-1 resize-none bg-transparent px-2 py-1.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none max-h-32 min-h-[38px]"
            />
            <Button
              type="submit"
              size="sm"
              disabled={!inputValue.trim() || isLoading}
              onClick={() => handleSend()}
              className="h-9 w-9 shrink-0 p-0 rounded-lg"
            >
              {isLoading ? <Loader2 size={16} className="animate-spin" /> : <Send size={15} />}
            </Button>
          </div>
          <p className="mt-1.5 text-center text-[10px] text-muted-foreground">
            Press <kbd className="rounded border border-border px-1">Enter</kbd> to send, <kbd className="rounded border border-border px-1">Shift + Enter</kbd> for new line.
          </p>
        </div>
      </div>
    </div>
  );
}
