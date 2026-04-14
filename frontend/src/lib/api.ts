/**
 * Typed axios client.
 *
 * - Attaches the in-memory access token to every request.
 * - On 401, attempts a silent token refresh then retries once.
 * - On second 401 (refresh failed), clears auth state and redirects to /login.
 */
import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '@/stores/auth';
import { clearRoleCookie } from '@/lib/auth';

const BASE_URL =
  typeof window === 'undefined'
    ? process.env.NEXT_PUBLIC_API_URL || 'http://api:8000'
    : ''; // browser → paths like /api/v1/... rewritten by next.config.mjs

export const apiClient = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  withCredentials: true, // send httpOnly refresh_token cookie
  headers: { 'Content-Type': 'application/json' },
});

// ---- Request interceptor: attach access token ----
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ---- Response interceptor: handle 401 with silent refresh ----
let _refreshing = false;
let _queue: Array<(token: string | null) => void> = [];

function _processQueue(token: string | null) {
  _queue.forEach((cb) => cb(token));
  _queue = [];
}

function _isAuthControlRequest(url?: string) {
  if (!url) return false;
  return ['/auth/login', '/auth/register', '/auth/refresh', '/auth/logout'].some((path) =>
    url.includes(path),
  );
}

function _isAuthPage() {
  if (typeof window === 'undefined') return false;
  return window.location.pathname === '/login' || window.location.pathname === '/register';
}

apiClient.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status !== 401 || original?._retry || _isAuthControlRequest(original?.url)) {
      return Promise.reject(error);
    }

    if (_refreshing) {
      // Queue request until refresh resolves
      return new Promise((resolve, reject) => {
        _queue.push((token) => {
          if (token) {
            original.headers.Authorization = `Bearer ${token}`;
            resolve(apiClient(original));
          } else {
            reject(error);
          }
        });
      });
    }

    original._retry = true;
    _refreshing = true;

    try {
      const { data } = await axios.post(
        `${BASE_URL}/api/v1/auth/refresh`,
        {},
        { withCredentials: true },
      );
      const newToken: string = data.access_token;
      useAuthStore.getState().setAccessToken(newToken);
      _processQueue(newToken);
      original.headers.Authorization = `Bearer ${newToken}`;
      return apiClient(original);
    } catch {
      _processQueue(null);
      useAuthStore.getState().clearAuth();
      if (typeof window !== 'undefined') {
        clearRoleCookie();
      }
      if (typeof window !== 'undefined' && !_isAuthPage()) {
        window.location.href = '/login';
      }
      return Promise.reject(error);
    } finally {
      _refreshing = false;
    }
  },
);

// ---------------------------------------------------------------------------
// Typed API helpers
// ---------------------------------------------------------------------------

export interface User {
  id: number;
  email: string;
  role: 'HR' | 'CANDIDATE';
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export const authApi = {
  login: (email: string, password: string) =>
    apiClient.post<AuthResponse>('/auth/login', { email, password }),

  register: (email: string, password: string, role: 'HR' | 'CANDIDATE') =>
    apiClient.post<AuthResponse>('/auth/register', { email, password, role }),

  refresh: () =>
    apiClient.post<{ access_token: string }>('/auth/refresh'),

  logout: () =>
    apiClient.post('/auth/logout'),

  me: () =>
    apiClient.get<User>('/auth/me'),
};

// ---------------------------------------------------------------------------
// Jobs
// ---------------------------------------------------------------------------

export interface CompanyOut {
  id: number;
  name: string;
  website?: string | null;
}

export interface JobOut {
  id: number;
  posted_by_user_id: number | null;
  title: string;
  description: string;
  required_skills: string[];
  min_experience: number | null;
  max_experience: number | null;
  min_salary: string | null;
  max_salary: string | null;
  location: string | null;
  employment_type: string;
  status: string;
  created_at: string;
  company: CompanyOut;
}

export interface JobListOut {
  total: number;
  items: JobOut[];
}

export interface MatchScoreOut {
  total: number;
  skill_overlap: number;
  semantic: number;
  experience_fit: number;
  salary_fit: number;
  location_fit: number;
  matched_skills: string[];
  missing_skills: string[];
}

export const jobsApi = {
  list: (params?: { skip?: number; limit?: number; location?: string }) =>
    apiClient.get<JobListOut>('/jobs', { params }),

  get: (jobId: number) =>
    apiClient.get<JobOut>(`/jobs/${jobId}`),

  matchScore: (jobId: number) =>
    apiClient.get<MatchScoreOut>(`/jobs/${jobId}/match-score`),
};

// ---------------------------------------------------------------------------
// Applications
// ---------------------------------------------------------------------------

export interface ApplicationOut {
  id: number;
  job_id: number;
  candidate_id: number;
  status: 'APPLIED' | 'SHORTLISTED' | 'INTERVIEW' | 'OFFERED' | 'HIRED' | 'REJECTED';
  cover_letter: string | null;
  match_score: string | null;
  created_at: string;
  job: JobOut;
}

export interface ApplicationListOut {
  total: number;
  items: ApplicationOut[];
}

export const applicationsApi = {
  apply: (jobId: number, coverLetter?: string) =>
    apiClient.post<ApplicationOut>('/applications', { job_id: jobId, cover_letter: coverLetter }),

  mine: (params?: { skip?: number; limit?: number }) =>
    apiClient.get<ApplicationListOut>('/applications/me', { params }),
};

// ---------------------------------------------------------------------------
// Profile & Resume
// ---------------------------------------------------------------------------

export interface CandidateProfileOut {
  id: number;
  user_id: number;
  full_name: string | null;
  headline: string | null;
  location: string | null;
  bio: string | null;
  years_experience: number | null;
  current_salary: number | null;
  expected_salary: number | null;
  notice_period_days: number | null;
  skills: string[] | null;
  resume_id: number | null;
}

export interface ResumeOut {
  id: number;
  candidate_id: number;
  original_filename: string;
  mime_type: string;
  parsed_skills: string[] | null;
  parsed_experience_years: number | null;
  created_at: string;
}

export const profileApi = {
  get: () =>
    apiClient.get<CandidateProfileOut>('/profile/me'),

  update: (data: Partial<Omit<CandidateProfileOut, 'id' | 'user_id' | 'resume_id'>>) =>
    apiClient.put<CandidateProfileOut>('/profile/me', data),

  uploadResume: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return apiClient.post<ResumeOut>('/resumes/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  myResumes: () =>
    apiClient.get<ResumeOut[]>('/resumes/me'),
};

// ---------------------------------------------------------------------------
// HR — Jobs management
// ---------------------------------------------------------------------------

export interface JobCreatePayload {
  title: string;
  description: string;
  required_skills: string[];
  company_name: string;
  min_experience?: number | null;
  max_experience?: number | null;
  min_salary?: number | null;
  max_salary?: number | null;
  location?: string | null;
  employment_type?: string;
}

export const hrJobsApi = {
  list: (params?: { skip?: number; limit?: number }) =>
    apiClient.get<JobListOut>('/jobs', { params }),

  create: (data: JobCreatePayload) =>
    apiClient.post<JobOut>('/jobs', data),

  updateStatus: (jobId: number, status: 'OPEN' | 'CLOSED') =>
    apiClient.patch<JobOut>(`/jobs/${jobId}`, { status }),

  delete: (jobId: number) =>
    apiClient.delete(`/jobs/${jobId}`),

  applications: (jobId: number) =>
    apiClient.get<ApplicationListOut>(`/jobs/${jobId}/applications`),

  rankedCandidates: (jobId: number, params?: { min_score?: number; limit?: number }) =>
    apiClient.get<RankedCandidateOut[]>(`/jobs/${jobId}/candidates/ranked`, { params }),
};

// ---------------------------------------------------------------------------
// HR — Smart candidate search
// ---------------------------------------------------------------------------

export interface CandidateSearchRequest {
  job_id?: number | null;
  query_text?: string | null;
  required_skills?: string[];
  min_experience?: number | null;
  max_experience?: number | null;
  min_score?: number;
  limit?: number;
}

export interface RankedCandidateOut {
  candidate_id: number;
  email: string;
  profile: CandidateProfileOut;
  score: MatchScoreOut;
}

export const hrCandidatesApi = {
  search: (body: CandidateSearchRequest) =>
    apiClient.post<RankedCandidateOut[]>('/candidates/search', body),
};

// ---------------------------------------------------------------------------
// HR — Invites
// ---------------------------------------------------------------------------

export const hrInvitesApi = {
  bulkInvite: (jobId: number, candidateIds: number[], message?: string) =>
    apiClient.post('/invites/bulk', { job_id: jobId, candidate_ids: candidateIds, message }),
};
