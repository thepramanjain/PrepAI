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
  content_type: string;
  upload_date: string;
}

/** Upload a PDF resume. Returns the stored resume document. */
export async function uploadResume(file: File): Promise<ResumeDoc> {
  const formData = new FormData();
  formData.append('file', file);

  const { data } = await api.post<ResumeDoc>('/api/resume', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

/** Get the current user's resume metadata. */
export async function getResume(): Promise<ResumeDoc | null> {
  try {
    const { data } = await api.get<ResumeDoc>('/api/resume');
    return data;
  } catch {
    return null;
  }
}

/** Delete the current user's resume. */
export async function deleteResume(): Promise<void> {
  await api.delete('/api/resume');
}
