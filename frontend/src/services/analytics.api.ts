/**
 * src/services/analytics.api.ts
 *
 * API calls for the Analytics endpoints.
 */

import api from './api';

/** Full analytics dashboard payload in one call. */
export async function getFullAnalytics(days?: number) {
  const { data } = await api.get('/api/analytics', { params: days ? { days } : {} });
  return data;
}

/** Legacy alias kept for compatibility. */
export async function getAnalytics() {
  return getFullAnalytics();
}

/** Score trend (line chart data) — was incorrectly called /weekly. */
export async function getScoreTrend(days?: number) {
  const { data } = await api.get('/api/analytics/score-trend', { params: days ? { days } : {} });
  return data;
}

/** @deprecated Use getScoreTrend instead */
export async function getWeeklyTrend() {
  return getScoreTrend(7);
}

export async function getTopicBreakdown() {
  const { data } = await api.get('/api/analytics/topics');
  return data;
}

export async function getInterviewHistory(page = 1, limit = 10, days?: number) {
  const { data } = await api.get('/api/analytics/history', { params: { page, limit, ...(days ? { days } : {}) } });
  return data;
}
