/**
 * src/services/resume.api.ts
 *
 * API calls for Resume upload and management.
 */

import api from './api';

export interface ResumeDoc {
  id: string;
  user_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  upload_date: string;
}

export interface ResumeListResponse {
  resumes: ResumeDoc[];
  total: number;
  page: number;
  limit: number;
}

/** Upload a PDF or DOCX resume. Returns the stored resume document. */
export async function uploadResume(file: File): Promise<ResumeDoc> {
  const formData = new FormData();
  formData.append('file', file);

  const { data } = await api.post<ResumeDoc>('/api/resumes/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

/** List the current user's resumes (paginated). */
export async function getResumes(page = 1, limit = 20): Promise<ResumeListResponse> {
  const { data } = await api.get<ResumeListResponse>('/api/resumes', { params: { page, limit } });
  return data;
}

/** Get a specific resume by ID. */
export async function getResume(resumeId: string): Promise<ResumeDoc | null> {
  try {
    const { data } = await api.get<ResumeDoc>(`/api/resumes/${resumeId}`);
    return data;
  } catch {
    return null;
  }
}

/** Delete a resume by ID. */
export async function deleteResume(resumeId: string): Promise<void> {
  await api.delete(`/api/resumes/${resumeId}`);
}
