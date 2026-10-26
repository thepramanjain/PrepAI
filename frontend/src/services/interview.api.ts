/**
 * src/services/interview.api.ts
 *
 * API calls for Interview management and the Text Interview Engine.
 */

import api from './api';

// ── Payload / Response types ────────────────────────────────────────────

export interface CreateInterviewPayload {
  title: string;
  role: string;
  experience_level: string;
  skills: string[];
  interview_type: string;
  difficulty: string;
  job_description?: string;
  mode: 'text' | 'voice';
  resume_id?: string;
}

export interface InterviewDoc {
  id: string;
  user_id: string;
  role: string;
  experience_level: string;
  skills: string[];
  difficulty: string;
  job_description?: string;
  mode: string;
  status: 'created' | 'active' | 'completed';
  created_at: string;
}

export interface QuestionDoc {
  id: string;
  interview_id: string;
  text: string;
  type: string;
  difficulty?: string;
  order: number;
}

export interface StartInterviewResponse {
  interview: InterviewDoc;
  current_question: QuestionDoc;
  question_number: number;
  total_questions: number;
}

export interface CurrentQuestionResponse {
  current_question: QuestionDoc;
  question_number: number;
  total_questions: number;
}

export interface SubmitAnswerResponse {
  response_id: string;
  question_id: string;
  feedback?: string;
  score?: number;
}

export interface NextQuestionResponse {
  interview?: InterviewDoc;
  current_question?: QuestionDoc;
  question_number?: number;
  total_questions?: number;
  completed?: boolean;
  final_score?: number;
}

// ── CRUD ────────────────────────────────────────────────────────────────

export async function createInterview(data: CreateInterviewPayload): Promise<InterviewDoc> {
  const { data: doc } = await api.post<InterviewDoc>('/api/interviews', data);
  return doc;
}

export async function getInterviews(page = 1, limit = 10) {
  const { data } = await api.get('/api/interviews', { params: { page, limit } });
  return data;
}

export async function getInterview(id: string): Promise<InterviewDoc> {
  const { data } = await api.get<InterviewDoc>(`/api/interviews/${id}`);
  return data;
}

// ── AI Question Generation ───────────────────────────────────────────────

export async function generateQuestions(
  interviewId: string,
  questionCount = 5,
): Promise<{ generated: number }> {
  const { data } = await api.post(`/api/ai/interviews/${interviewId}/generate-questions`, {
    question_count: questionCount,
  });
  return data;
}

// ── Interview Engine ─────────────────────────────────────────────────────

export async function startInterview(interviewId: string): Promise<StartInterviewResponse> {
  const { data } = await api.post<StartInterviewResponse>(
    `/api/interviews/${interviewId}/start`,
  );
  return data;
}

export async function getCurrentQuestion(
  interviewId: string,
): Promise<CurrentQuestionResponse> {
  const { data } = await api.get<CurrentQuestionResponse>(
    `/api/interviews/${interviewId}/current-question`,
  );
  return data;
}

export async function submitAnswer(
  interviewId: string,
  questionId: string,
  answer: string,
  durationSeconds?: number,
): Promise<SubmitAnswerResponse> {
  const { data } = await api.post<SubmitAnswerResponse>(
    `/api/interviews/${interviewId}/questions/${questionId}/response`,
    { answer, duration_seconds: durationSeconds },
  );
  return data;
}

export async function nextQuestion(interviewId: string): Promise<NextQuestionResponse> {
  const { data } = await api.post<NextQuestionResponse>(
    `/api/interviews/${interviewId}/next`,
  );
  return data;
}
