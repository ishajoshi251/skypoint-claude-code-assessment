'use client';

import { useQueries, useQuery } from '@tanstack/react-query';
import { Briefcase, Search } from 'lucide-react';
import { jobsApi, applicationsApi } from '@/lib/api';
import { JobCard } from '@/components/jobs/job-card';

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
  const { data: jobsData, isLoading: jobsLoading, isError } = useQuery({
    queryKey: ['jobs', 'list'],
    queryFn: () => jobsApi.list({ limit: 20 }).then((r) => r.data),
  });

  const { data: appsData } = useQuery({
    queryKey: ['applications', 'mine'],
    queryFn: () => applicationsApi.mine().then((r) => r.data),
  });

  const appliedJobIds = new Set(appsData?.items.map((a) => a.job_id) ?? []);

  // Fetch match scores for all jobs in parallel
  const scoreQueries = useQueries({
    queries: (jobsData?.items ?? []).map((job) => ({
      queryKey: ['match-score', job.id],
      queryFn: () => jobsApi.matchScore(job.id).then((r) => r.data),
      staleTime: 5 * 60 * 1000,
    })),
  });

  const jobs = jobsData?.items ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Browse Jobs</h1>
        <p className="text-muted-foreground">
          {jobsData ? `${jobsData.total} open positions — match scores personalised to your profile` : 'Find your next opportunity'}
        </p>
      </div>

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
