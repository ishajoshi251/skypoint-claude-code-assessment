'use client';

import { useQueries, useQuery } from '@tanstack/react-query';
import { Briefcase, FileText, Star, TrendingUp } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { jobsApi, applicationsApi, profileApi, type CandidateProfileOut } from '@/lib/api';
import { JobCard } from '@/components/jobs/job-card';

function computeProfileStrength(profile: CandidateProfileOut | undefined) {
  if (!profile) return 0;
  const checks = [
    profile.full_name, profile.headline, profile.bio,
    profile.skills?.length, profile.years_experience,
    profile.location, profile.resume_id, profile.expected_salary,
  ];
  const weights = [15, 10, 10, 20, 10, 5, 25, 5];
  return checks.reduce<number>((acc, v, i) => acc + (v ? weights[i] : 0), 0);
}

export default function CandidateDashboard() {
  const { data: profile } = useQuery({
    queryKey: ['profile', 'me'],
    queryFn: () => profileApi.get().then((r) => r.data),
  });

  const { data: appsData } = useQuery({
    queryKey: ['applications', 'mine'],
    queryFn: () => applicationsApi.mine({ limit: 50 }).then((r) => r.data),
  });

  const { data: jobsData } = useQuery({
    queryKey: ['jobs', 'list'],
    queryFn: () => jobsApi.list({ limit: 10 }).then((r) => r.data),
  });

  const appliedJobIds = new Set(appsData?.items.map((a) => a.job_id) ?? []);
  const jobs = jobsData?.items ?? [];
  const profileStrength = computeProfileStrength(profile);

  const scoreQueries = useQueries({
    queries: jobs.map((job) => ({
      queryKey: ['match-score', job.id],
      queryFn: () => jobsApi.matchScore(job.id).then((r) => r.data),
      staleTime: 5 * 60 * 1000,
    })),
  });

  const scoredJobs = jobs
    .map((job, i) => ({ job, score: scoreQueries[i]?.data }))
    .filter((j) => j.score !== undefined)
    .sort((a, b) => (b.score?.total ?? 0) - (a.score?.total ?? 0))
    .slice(0, 3);

  const bestScore = scoredJobs[0]?.score?.total ?? 0;
  const scoresLoading = scoreQueries.some((q) => q.isLoading);

  const STATS = [
    {
      label: 'Best Match',
      value: scoresLoading ? '…' : bestScore > 0 ? `${Math.round(bestScore)}%` : '—',
      icon: Star,
      desc: 'Top match across open jobs',
    },
    {
      label: 'Applications',
      value: appsData ? String(appsData.total) : '—',
      icon: FileText,
      desc: 'Jobs you have applied to',
    },
    {
      label: 'Open Jobs',
      value: jobsData ? String(jobsData.total) : '—',
      icon: Briefcase,
      desc: 'Positions currently open',
    },
    {
      label: 'Profile Strength',
      value: profile ? `${profileStrength}%` : '—',
      icon: TrendingUp,
      desc: profile?.resume_id ? 'Great — keep it updated' : 'Upload a resume to boost',
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Welcome back</h1>
        <p className="text-muted-foreground">Here&apos;s a snapshot of your job search activity.</p>
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {STATS.map(({ label, value, icon: Icon, desc }) => (
          <Card key={label}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">{label}</CardTitle>
              <Icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{value}</div>
              <p className="text-xs text-muted-foreground mt-1">{desc}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Top matches */}
      {scoredJobs.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Top Matches For You</h2>
            <a href="/candidate/jobs" className="text-sm text-brand-600 hover:underline">View all →</a>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {scoredJobs.map(({ job, score }) => (
              <JobCard key={job.id} job={job} matchScore={score} alreadyApplied={appliedJobIds.has(job.id)} />
            ))}
          </div>
        </div>
      )}

      {/* CTA when profile is weak */}
      {profileStrength < 50 && (
        <Card className="border-brand-200 bg-brand-50 dark:bg-brand-900/20">
          <CardHeader>
            <CardTitle className="text-brand-700 dark:text-brand-300">Complete your profile</CardTitle>
            <CardDescription>
              Add your skills, upload a resume, and unlock personalised job match scores.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <a
              href="/candidate/profile"
              className="inline-flex items-center gap-2 rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 transition-colors"
            >
              Go to Profile →
            </a>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
