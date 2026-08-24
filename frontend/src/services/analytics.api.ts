/**
 * src/services/analytics.api.ts
 *
 * API calls for the Analytics endpoints.
 */

import api from './api';

export async function getAnalytics() {
  const { data } = await api.get('/api/analytics');
  return data;
}

export async function getWeeklyTrend() {
  const { data } = await api.get('/api/analytics/weekly');
  return data;
}

export async function getTopicBreakdown() {
  const { data } = await api.get('/api/analytics/topics');
  return data;
}
