/**
 * src/services/agent.api.ts
 *
 * API client for the PrepAI Agentic AI / Career Coach (Phase 10).
 * Connects frontend to backend POST /api/agent/run.
 */

import api from './api';

export interface ActionItem {
  task: string;
  reason: string;
  priority: 'low' | 'medium' | 'high';
}

export interface CoachingResult {
  summary: string;
  strengths: string[];
  priority_weaknesses: string[];
  focus_topics: string[];
  action_plan: ActionItem[];
}

export interface AgentRequest {
  message: string;
  interview_id?: string;
}

export interface AgentResponse {
  success: boolean;
  task?: string;
  response: string;
  data?: {
    coaching?: CoachingResult;
    analytics?: Record<string, any>;
    questions?: Record<string, any>;
    [key: string]: any;
  };
}

/**
 * Send a natural-language message to the PrepAI Agent / Career Coach.
 * The GPT-4o orchestrator classifies intent, invokes tools, and returns
 * structured guidance and answers.
 */
export async function runAgent(message: string, interviewId?: string): Promise<AgentResponse> {
  const payload: AgentRequest = { message: message.trim() };
  if (interviewId) {
    payload.interview_id = interviewId;
  }

  const { data } = await api.post<AgentResponse>('/api/agent/run', payload);
  return data;
}
