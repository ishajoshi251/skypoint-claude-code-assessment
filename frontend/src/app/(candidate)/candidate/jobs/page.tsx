'use client';

import { useState } from 'react';
import type { FormEvent } from 'react';
import { useQueries, useQuery } from '@tanstack/react-query';
import { Briefcase, ChevronDown, Search } from 'lucide-react';
import { jobsApi, applicationsApi } from '@/lib/api';
import { JobCard } from '@/components/jobs/job-card';
import { useAuthStore } from '@/stores/auth';

const EXPERIENCE_OPTIONS = [
  { label: 'Select experience', value: '' },
  { label: 'Fresher', value: '0' },
  { label: '1 year', value: '1' },
  { label: '2 years', value: '2' },
  { label: '3 years', value: '3' },
  { label: '5 years', value: '5' },
  { label: '8+ years', value: '8' },
];

function JobCardSkeleton() {
  return (
    <div className="rounded-xl border bg-card p-5 space-y-3 animate-pulse">
      <div className="flex justify-between">
        <div className="space-y-2 flex-1">
          <div className="h-4 w-2/3 bg-muted rounded" />
          <div className="h-3 w-1/3 bg-muted rounded" />
        </div>
        <div className="h-14 w-14 rounded-full bg-muted" />
      </div>
      <div className="flex gap-2">
        {[1, 2, 3].map((i) => <div key={i} className="h-5 w-16 bg-muted rounded-full" />)}
      </div>
      <div className="h-3 w-full bg-muted rounded" />
      <div className="h-3 w-4/5 bg-muted rounded" />
    </div>
  );
}

export default function CandidateJobsPage() {
  const userId = useAuthStore((s) => s.user?.id);
  const [keywordInput, setKeywordInput] = useState('');
  const [locationInput, setLocationInput] = useState('');
  const [experienceInput, setExperienceInput] = useState('');
  const [filters, setFilters] = useState({ keyword: '', location: '', experience: '' });

  const activeSearch = Boolean(filters.keyword || filters.location || filters.experience);

  const { data: jobsData, isLoading: jobsLoading, isError } = useQuery({
    queryKey: ['jobs', 'list', filters],
    queryFn: () =>
      jobsApi
        .list({
          limit: 20,
          q: filters.keyword || undefined,
          location: filters.location || undefined,
          experience: filters.experience ? Number(filters.experience) : undefined,
        })
        .then((r) => r.data),
  });

  const { data: appsData } = useQuery({
    queryKey: ['applications', 'mine', userId],
    queryFn: () => applicationsApi.mine().then((r) => r.data),
    enabled: !!userId,
  });

  const appliedJobIds = new Set(appsData?.items.map((a) => a.job_id) ?? []);

  // Fetch match scores for all jobs in parallel
  const scoreQueries = useQueries({
    queries: (jobsData?.items ?? []).map((job) => ({
      queryKey: ['match-score', userId, job.id],
      queryFn: () => jobsApi.matchScore(job.id).then((r) => r.data),
      enabled: !!userId,
      staleTime: 5 * 60 * 1000,
    })),
  });

  const jobs = jobsData?.items ?? [];

  function handleSearch(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setFilters({
      keyword: keywordInput.trim(),
      location: locationInput.trim(),
      experience: experienceInput,
    });
  }

  function clearSearch() {
    setKeywordInput('');
    setLocationInput('');
    setExperienceInput('');
    setFilters({ keyword: '', location: '', experience: '' });
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Browse Jobs</h1>
        <p className="text-muted-foreground">
          {jobsData ? `${jobsData.total} open positions — match scores personalised to your profile` : 'Find your next opportunity'}
        </p>
      </div>

      <form
        onSubmit={handleSearch}
        className="flex w-full flex-col gap-3 rounded-[8px] border bg-white p-3 shadow-sm dark:bg-slate-900 md:flex-row md:items-center md:gap-0 md:rounded-full md:p-2"
      >
        <div className="flex min-w-0 flex-1 items-center px-3 md:px-5">
          <input
            value={keywordInput}
            onChange={(e) => setKeywordInput(e.target.value)}
            className="h-11 w-full bg-transparent text-sm font-medium outline-none placeholder:text-slate-400 md:text-base"
            placeholder="Enter keyword / designation / companies"
          />
        </div>

        <div className="hidden h-8 w-px bg-border md:block" />

        <div className="relative flex min-w-0 flex-1 items-center px-3 md:max-w-[250px] md:px-5">
          <select
            value={experienceInput}
            onChange={(e) => setExperienceInput(e.target.value)}
            className="h-11 w-full appearance-none bg-transparent pr-8 text-sm font-medium text-slate-500 outline-none md:text-base"
            aria-label="Select experience"
          >
            {EXPERIENCE_OPTIONS.map((option) => (
              <option key={option.label} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <ChevronDown className="pointer-events-none absolute right-3 h-4 w-4 text-slate-500 md:right-5" />
        </div>

        <div className="hidden h-8 w-px bg-border md:block" />

        <div className="flex min-w-0 flex-1 items-center px-3 md:px-5">
          <input
            value={locationInput}
            onChange={(e) => setLocationInput(e.target.value)}
            className="h-11 w-full bg-transparent text-sm font-medium outline-none placeholder:text-slate-400 md:text-base"
            placeholder="Enter location"
          />
        </div>

        <div className="flex items-center gap-2 md:ml-2">
          {activeSearch && (
            <button
              type="button"
              onClick={clearSearch}
              className="h-11 rounded-[8px] px-4 text-sm font-semibold text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
            >
              Clear
            </button>
          )}
          <button
            type="submit"
            className="flex h-11 flex-1 items-center justify-center gap-2 rounded-[8px] bg-blue-600 px-6 text-sm font-bold text-white shadow-sm hover:bg-blue-700 md:flex-none md:px-8 md:text-base"
          >
            <Search className="h-5 w-5" />
            Search
          </button>
        </div>
      </form>

      {isError && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          Failed to load jobs. Please refresh.
        </div>
      )}

      {jobsLoading && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => <JobCardSkeleton key={i} />)}
        </div>
      )}

      {!jobsLoading && jobs.length === 0 && !isError && (
        <div className="flex flex-col items-center gap-4 rounded-lg border border-dashed p-16 text-center">
          <Briefcase className="h-10 w-10 text-muted-foreground" />
          <div>
            <p className="font-medium">No open jobs yet</p>
            <p className="text-sm text-muted-foreground mt-1">Check back soon — HR teams are posting new roles.</p>
          </div>
        </div>
      )}

      {!jobsLoading && jobs.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {jobs.map((job, idx) => (
            <JobCard
              key={job.id}
              job={job}
              matchScore={scoreQueries[idx]?.data}
              alreadyApplied={appliedJobIds.has(job.id)}
              userId={userId}
            />
          ))}
        </div>
      )}

      {jobsData && jobsData.total > 20 && (
        <p className="text-center text-sm text-muted-foreground">
          Showing 20 of {jobsData.total} jobs.
        </p>
      )}
    </div>
  );
}
