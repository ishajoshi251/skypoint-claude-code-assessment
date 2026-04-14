'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Briefcase, MapPin, Users, ToggleLeft, ToggleRight, Trash2 } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';
import { hrJobsApi, type JobOut } from '@/lib/api';
import { useAuthStore } from '@/stores/auth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

function JobRow({ job }: { job: JobOut }) {
  const qc = useQueryClient();
  const isOpen = job.status === 'OPEN';

  const toggleMutation = useMutation({
    mutationFn: () => hrJobsApi.updateStatus(job.id, isOpen ? 'CLOSED' : 'OPEN'),
    onSuccess: () => {
      toast.success(`Job marked as ${isOpen ? 'closed' : 'open'}.`);
      qc.invalidateQueries({ queryKey: ['hr', 'jobs'] });
    },
    onError: () => toast.error('Failed to update status.'),
  });

  const deleteMutation = useMutation({
    mutationFn: () => hrJobsApi.delete(job.id),
    onSuccess: () => {
      toast.success('Job deleted.');
      qc.invalidateQueries({ queryKey: ['hr', 'jobs'] });
    },
    onError: () => toast.error('Failed to delete job.'),
  });

  function confirmDelete() {
    if (confirm(`Delete "${job.title}"? This cannot be undone.`)) {
      deleteMutation.mutate();
    }
  }

  return (
    <div className="flex items-center gap-4 rounded-lg border bg-card px-4 py-3 hover:shadow-sm transition-shadow">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium truncate">{job.title}</span>
          <span className={cn(
            'rounded-full px-2 py-0.5 text-[11px] font-semibold',
            isOpen
              ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
              : 'bg-slate-100 text-slate-500 dark:bg-slate-800',
          )}>
            {isOpen ? 'Open' : 'Closed'}
          </span>
        </div>
        <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-muted-foreground">
          <span>{job.company.name}</span>
          {job.location && (
            <span className="flex items-center gap-1"><MapPin className="h-3 w-3" />{job.location}</span>
          )}
          {(job.min_salary || job.max_salary) && (
            <span>
              {job.min_salary ? `$${Number(job.min_salary).toLocaleString()}` : ''}
              {job.min_salary && job.max_salary ? ' – ' : ''}
              {job.max_salary ? `$${Number(job.max_salary).toLocaleString()}` : ''}
            </span>
          )}
          <span>{job.required_skills.slice(0, 3).join(', ')}{job.required_skills.length > 3 ? ` +${job.required_skills.length - 3}` : ''}</span>
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <Link href={`/hr/candidates?job_id=${job.id}`}>
          <Button variant="outline" size="sm" className="gap-1.5 text-xs">
            <Users className="h-3.5 w-3.5" /> Find Candidates
          </Button>
        </Link>
        <Button
          variant="ghost" size="sm"
          onClick={() => toggleMutation.mutate()}
          disabled={toggleMutation.isPending}
          title={isOpen ? 'Close job' : 'Reopen job'}
        >
          {isOpen
            ? <ToggleRight className="h-4 w-4 text-green-600" />
            : <ToggleLeft className="h-4 w-4 text-muted-foreground" />}
        </Button>
        <Button
          variant="ghost" size="sm"
          onClick={confirmDelete}
          disabled={deleteMutation.isPending}
          title="Delete job"
        >
          <Trash2 className="h-4 w-4 text-destructive" />
        </Button>
      </div>
    </div>
  );
}

export default function HrJobsPage() {
  const { user } = useAuthStore();

  const { data, isLoading } = useQuery({
    queryKey: ['hr', 'jobs'],
    queryFn: () => hrJobsApi.list({ limit: 100 }).then((r) => r.data),
  });

  const myJobs = (data?.items ?? []).filter((j) => j.posted_by_user_id === user?.id);
  const openCount = myJobs.filter((j) => j.status === 'OPEN').length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">My Jobs</h1>
          <p className="text-muted-foreground">
            {data ? `${openCount} open · ${myJobs.length} total` : 'Your job postings'}
          </p>
        </div>
        <Link href="/hr/jobs/new">
          <Button className="gap-2">
            <Plus className="h-4 w-4" /> Post a Job
          </Button>
        </Link>
      </div>

      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-16 rounded-lg border bg-card animate-pulse" />
          ))}
        </div>
      )}

      {!isLoading && myJobs.length === 0 && (
        <div className="flex flex-col items-center gap-4 rounded-lg border border-dashed p-16 text-center">
          <Briefcase className="h-10 w-10 text-muted-foreground" />
          <div>
            <p className="font-medium">No jobs posted yet</p>
            <p className="text-sm text-muted-foreground mt-1">Post your first job to start finding candidates.</p>
          </div>
          <Link href="/hr/jobs/new">
            <Button className="gap-2"><Plus className="h-4 w-4" /> Post a Job</Button>
          </Link>
        </div>
      )}

      {!isLoading && myJobs.length > 0 && (
        <div className="space-y-2">
          {myJobs.map((job) => <JobRow key={job.id} job={job} />)}
        </div>
      )}
    </div>
  );
}
