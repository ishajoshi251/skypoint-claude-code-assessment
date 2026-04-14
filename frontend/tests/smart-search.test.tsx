/**
 * Smart-search API payload tests.
 *
 * The candidates page calls hrCandidatesApi.search() with a structured body.
 * We test that the API module builds the correct payload shapes — this is the
 * unit-testable core of the smart-search feature without rendering the full page
 * (which requires QueryClient, auth store, and router context).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the axios client so no real HTTP goes out
vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>();
  return {
    ...actual,
    apiClient: {
      post: vi.fn(),
      get: vi.fn(),
    },
  };
});

import { hrCandidatesApi, type CandidateSearchRequest } from '@/lib/api';

describe('hrCandidatesApi.search — payload shapes', () => {
  beforeEach(() => vi.clearAllMocks());

  it('sends required_skills array when provided', async () => {
    const { apiClient } = await import('@/lib/api');
    (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: [] });

    const payload: CandidateSearchRequest = {
      required_skills: ['python', 'fastapi'],
      min_score: 0,
      limit: 30,
    };
    await hrCandidatesApi.search(payload);

    expect(apiClient.post).toHaveBeenCalledWith(
      '/candidates/search',
      expect.objectContaining({ required_skills: ['python', 'fastapi'] }),
    );
  });

  it('sends job_id when matching against a specific job', async () => {
    const { apiClient } = await import('@/lib/api');
    (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: [] });

    const payload: CandidateSearchRequest = { job_id: 42, min_score: 0, limit: 30 };
    await hrCandidatesApi.search(payload);

    expect(apiClient.post).toHaveBeenCalledWith(
      '/candidates/search',
      expect.objectContaining({ job_id: 42 }),
    );
  });

  it('sends query_text for free-text JD search', async () => {
    const { apiClient } = await import('@/lib/api');
    (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: [] });

    const jd = 'Senior Python developer with FastAPI and PostgreSQL experience';
    const payload: CandidateSearchRequest = { query_text: jd, min_score: 0, limit: 30 };
    await hrCandidatesApi.search(payload);

    expect(apiClient.post).toHaveBeenCalledWith(
      '/candidates/search',
      expect.objectContaining({ query_text: jd }),
    );
  });

  it('sends min_score filter', async () => {
    const { apiClient } = await import('@/lib/api');
    (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: [] });

    await hrCandidatesApi.search({ required_skills: ['python'], min_score: 70, limit: 30 });

    expect(apiClient.post).toHaveBeenCalledWith(
      '/candidates/search',
      expect.objectContaining({ min_score: 70 }),
    );
  });

  it('returns the data from the response', async () => {
    const { apiClient } = await import('@/lib/api');
    const mockResult = [
      {
        candidate_id: 1,
        email: 'dev@example.com',
        profile: { user_id: 1, skills: ['python'], full_name: 'Dev One' },
        score: { total: 85, skill_overlap: 90, semantic: 80, experience_fit: 85,
                 salary_fit: 75, location_fit: 100, matched_skills: ['python'], missing_skills: [] },
      },
    ];
    (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockResult });

    const result = await hrCandidatesApi.search({ required_skills: ['python'], min_score: 0 });
    expect(result.data).toEqual(mockResult);
    expect(result.data[0].score.total).toBe(85);
    expect(result.data[0].score.matched_skills).toContain('python');
  });
});
