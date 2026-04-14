'use client';

import { useQuery } from '@tanstack/react-query';
import { Briefcase, Users, Send, TrendingUp, Plus, Search } from 'lucide-react';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { hrJobsApi, type JobOut } from '@/lib/api';
import { useAuthStore } from '@/stores/auth';
import { cn } from '@/lib/utils';

function JobStatusBadge({ status }: { status: string }) {
  return (
    <span className={cn(
      'rounded-full px-2 py-0.5 text-[11px] font-semibold',
      status === 'OPEN'
        ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
        : 'bg-slate-100 text-slate-500 dark:bg-slate-800',
    )}>
      {status === 'OPEN' ? 'Open' : 'Closed'}
    </span>
  );
}

function RecentJobRow({ job }: { job: JobOut }) {
  return (
    <div className="flex items-center justify-between gap-3 py-2.5 border-b last:border-0">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <p className="font-medium text-sm truncate">{job.title}</p>
          <JobStatusBadge status={job.status} />
        </div>
        <p className="text-xs text-muted-foreground mt-0.5">
          {job.company.name}{job.location ? ` · ${job.location}` : ''}
        </p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <Link href={`/hr/candidates?job_id=${job.id}`}>
          <Button variant="outline" size="sm" className="text-xs gap-1">
            <Users className="h-3 w-3" /> Find Candidates
          </Button>
        </Link>
        <Link href={`/hr/pipeline?job_id=${job.id}`}>
          <Button variant="ghost" size="sm" className="text-xs">Pipeline</Button>
        </Link>
      </div>
    </div>
  );
}

export default function HrDashboard() {
  const { user } = useAuthStore();

  const { data: jobsData } = useQuery({
    queryKey: ['hr', 'jobs'],
    queryFn: () => hrJobsApi.list({ limit: 100 }).then((r) => r.data),
  });

  const myJobs = (jobsData?.items ?? []).filter((j) => j.posted_by_user_id === user?.id);
  const openJobs = myJobs.filter((j) => j.status === 'OPEN');
  const recentJobs = myJobs.slice(0, 5);

  const STATS = [
    {
      label: 'Active Jobs',
      value: jobsData ? String(openJobs.length) : '—',
      icon: Briefcase,
      desc: 'Open positions posted by you',
    },
    {
      label: 'Total Postings',
      value: jobsData ? String(myJobs.length) : '—',
      icon: TrendingUp,
      desc: 'All jobs you have posted',
    },
    {
      label: 'Candidates Available',
      value: '—',
      icon: Users,
      desc: 'Run a smart search to see matches',
    },
    {
      label: 'Invites Sent',
      value: '—',
      icon: Send,
      desc: 'Personalised outreach emails',
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">HR Dashboard</h1>
          <p className="text-muted-foreground">Manage your jobs, find great candidates, and track your pipeline.</p>
        </div>
        <Link href="/hr/jobs/new">
          <Button className="gap-2"><Plus className="h-4 w-4" /> Post a Job</Button>
        </Link>
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

      {/* Quick actions */}
      <div className="grid gap-4 sm:grid-cols-2">
        <Card className="border-brand-200 bg-brand-50 dark:bg-brand-900/20">
          <CardHeader>
            <CardTitle className="text-brand-700 dark:text-brand-300">Post a New Job</CardTitle>
            <CardDescription>Create a job posting and let TalentBridge rank matching candidates automatically.</CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/hr/jobs/new"
              className="inline-flex items-center gap-2 rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 transition-colors">
              <Plus className="h-4 w-4" /> Create Job
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Smart Candidate Search</CardTitle>
            <CardDescription>Paste a job description to instantly find and rank the best-fit candidates.</CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/hr/candidates"
              className="inline-flex items-center gap-2 rounded-md border border-brand-600 px-4 py-2 text-sm font-medium text-brand-600 hover:bg-brand-50 transition-colors">
              <Search className="h-4 w-4" /> Search Candidates
            </Link>
          </CardContent>
        </Card>
      </div>

      {/* Recent jobs */}
      {recentJobs.length > 0 && (
        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardTitle className="text-base">Recent Jobs</CardTitle>
            <Link href="/hr/jobs" className="text-sm text-brand-600 hover:underline">View all →</Link>
          </CardHeader>
          <CardContent className="pt-0">
            {recentJobs.map((job) => <RecentJobRow key={job.id} job={job} />)}
          </CardContent>
        </Card>
      )}

      {jobsData && myJobs.length === 0 && (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <Briefcase className="h-10 w-10 text-muted-foreground" />
            <div>
              <p className="font-medium">No jobs posted yet</p>
              <p className="text-sm text-muted-foreground mt-1">Post your first job to start finding candidates.</p>
            </div>
            <Link href="/hr/jobs/new">
              <Button className="gap-2"><Plus className="h-4 w-4" /> Post a Job</Button>
            </Link>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
