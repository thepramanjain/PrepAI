/**
 * src/services/feedback.api.ts
 *
 * API calls for AI Evaluation & Feedback (Phase 7).
 */

import api from './api';

export interface CategoryScores {
  technical: number;
  communication: number;
  problem_solving: number;
  relevance: number;
}

export interface QuestionEvaluation {
  question_id: string;
  score: number;
  quality: string;
  strengths: string[];
  improvements: string[];
  feedback: string;
}

export interface TopicAnalysis {
  topic: string;
  score: number;
  assessment: string;
}

export interface FeedbackResponse {
  id: string;
  interview_id: string;
  user_id: string;
  overall_score: number;
  category_scores: CategoryScores;
  question_evaluations: QuestionEvaluation[];
  strengths: string[];
  weaknesses: string[];
  recommendations: string[];
  topic_analysis: TopicAnalysis[];
  summary: string;
  created_at: string;
  updated_at?: string;
}

/** Trigger AI evaluation for a completed interview. */
export async function evaluateInterview(interviewId: string): Promise<FeedbackResponse> {
  const { data } = await api.post<FeedbackResponse>(`/api/interviews/${interviewId}/evaluate`);
  return data;
}

/** Retrieve existing AI feedback for an interview. */
export async function getFeedback(interviewId: string): Promise<FeedbackResponse> {
  const { data } = await api.get<FeedbackResponse>(`/api/interviews/${interviewId}/feedback`);
  return data;
}
