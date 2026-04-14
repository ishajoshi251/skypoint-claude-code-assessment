'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { hrJobsApi, applicationsApi, type ApplicationOut } from '@/lib/api';
import { useAuthStore } from '@/stores/auth';
import { apiClient } from '@/lib/api';
import { cn } from '@/lib/utils';

type Stage = ApplicationOut['status'];

const STAGES: { key: Stage; label: string; color: string }[] = [
  { key: 'APPLIED',     label: 'Applied',     color: 'border-t-blue-400' },
  { key: 'SHORTLISTED', label: 'Shortlisted', color: 'border-t-yellow-400' },
  { key: 'INTERVIEW',   label: 'Interview',   color: 'border-t-orange-400' },
  { key: 'OFFERED',     label: 'Offered',     color: 'border-t-purple-400' },
  { key: 'HIRED',       label: 'Hired',       color: 'border-t-green-400' },
];

const STAGE_BADGE: Record<Stage, string> = {
  APPLIED:     'bg-blue-100 text-blue-700',
  SHORTLISTED: 'bg-yellow-100 text-yellow-700',
  INTERVIEW:   'bg-orange-100 text-orange-700',
  OFFERED:     'bg-purple-100 text-purple-700',
  HIRED:       'bg-green-100 text-green-700',
  REJECTED:    'bg-red-100 text-red-700',
};

function ApplicationCard({
  app,
  onMove,
}: {
  app: ApplicationOut;
  onMove: (status: Stage) => void;
}) {
  const stages = STAGES.map((s) => s.key);
  const idx = stages.indexOf(app.status as Stage);

  return (
    <div className="rounded-lg border bg-white dark:bg-slate-900 p-3 shadow-sm space-y-2 cursor-default">
      <div>
        <p className="font-medium text-sm leading-tight">{app.job.title}</p>
        <p className="text-xs text-muted-foreground">{app.job.company.name}</p>
      </div>

      {app.match_score && (
        <p className="text-xs font-semibold text-brand-600">{Math.round(Number(app.match_score))}% match</p>
      )}

      <p className="text-xs text-muted-foreground">
        Applied {new Date(app.created_at).toLocaleDateString()}
      </p>

      {/* Move controls */}
      <div className="flex gap-1 pt-1">
        {idx > 0 && (
          <button
            onClick={() => onMove(stages[idx - 1])}
            className="flex-1 rounded text-[10px] font-medium py-1 bg-muted hover:bg-muted/80 transition-colors"
          >
            ← {STAGES[idx - 1].label}
          </button>
        )}
        {idx < STAGES.length - 1 && (
          <button
            onClick={() => onMove(stages[idx + 1])}
            className="flex-1 rounded text-[10px] font-medium py-1 bg-brand-600 text-white hover:bg-brand-700 transition-colors"
          >
            {STAGES[idx + 1].label} →
          </button>
        )}
        <button
          onClick={() => onMove('REJECTED')}
          className="rounded text-[10px] font-medium px-2 py-1 bg-red-100 text-red-700 hover:bg-red-200 transition-colors"
          title="Reject"
        >
          ✕
        </button>
      </div>
    </div>
  );
}

export default function HrPipelinePage() {
  const { user } = useAuthStore();
  const qc = useQueryClient();
  const [selectedJobId, setSelectedJobId] = useState<string>('');

  const { data: jobsData } = useQuery({
    queryKey: ['hr', 'jobs'],
    queryFn: () => hrJobsApi.list({ limit: 100 }).then((r) => r.data),
  });

  const myJobs = (jobsData?.items ?? []).filter((j) => j.posted_by_user_id === user?.id);

  const { data: appsData, isLoading } = useQuery({
    queryKey: ['hr', 'applications', selectedJobId],
    queryFn: async () => {
      if (!selectedJobId) return null;
      const r = await hrJobsApi.applications(Number(selectedJobId));
      return r.data;
    },
    enabled: !!selectedJobId,
  });

  const moveMutation = useMutation({
    mutationFn: ({ appId, status }: { appId: number; status: Stage | 'REJECTED' }) =>
      apiClient.patch(`/applications/${appId}/status`, { status }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['hr', 'applications', selectedJobId] });
    },
    onError: () => toast.error('Failed to update status.'),
  });

  const apps = appsData?.items ?? [];

  const byStage = (stage: string) => apps.filter((a) => a.status === stage);
  const rejected = apps.filter((a) => a.status === 'REJECTED');

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Pipeline</h1>
        <p className="text-muted-foreground">Move candidates through your hiring stages.</p>
      </div>

      {/* Job selector */}
      <div className="max-w-sm">
        <label className="text-sm font-medium mb-1.5 block">Select a Job</label>
        <select
          value={selectedJobId}
          onChange={(e) => setSelectedJobId(e.target.value)}
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="">— Choose a job to view pipeline —</option>
          {myJobs.map((j) => (
            <option key={j.id} value={j.id}>{j.title} · {j.company.name}</option>
          ))}
        </select>
      </div>

      {!selectedJobId && (
        <div className="rounded-lg border border-dashed p-12 text-center text-muted-foreground">
          Select a job above to view its candidate pipeline.
        </div>
      )}

      {selectedJobId && isLoading && (
        <div className="grid grid-cols-5 gap-3">
          {STAGES.map((s) => (
            <div key={s.key} className="h-48 rounded-lg border animate-pulse bg-muted" />
          ))}
        </div>
      )}

      {selectedJobId && !isLoading && apps.length === 0 && (
        <div className="rounded-lg border border-dashed p-12 text-center text-muted-foreground">
          No applications yet for this job.
        </div>
      )}

      {selectedJobId && !isLoading && apps.length > 0 && (
        <div className="space-y-4">
          {/* Summary */}
          <div className="flex flex-wrap gap-2">
            {STAGES.map((s) => {
              const count = byStage(s.key).length;
              return (
                <span key={s.key} className={cn('rounded-full px-3 py-1 text-xs font-medium', STAGE_BADGE[s.key])}>
                  {s.label}: {count}
                </span>
              );
            })}
            {rejected.length > 0 && (
              <span className={cn('rounded-full px-3 py-1 text-xs font-medium', STAGE_BADGE['REJECTED'])}>
                Rejected: {rejected.length}
              </span>
            )}
          </div>

          {/* Kanban board */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5 overflow-x-auto">
            {STAGES.map((stage) => (
              <div key={stage.key} className={cn('rounded-lg border-t-4 bg-muted/30 p-3 min-h-[200px] space-y-2', stage.color)}>
                <div className="flex items-center justify-between mb-1">
                  <p className="text-sm font-semibold">{stage.label}</p>
                  <span className="rounded-full bg-muted px-2 text-xs font-medium">{byStage(stage.key).length}</span>
                </div>
                {byStage(stage.key).map((app) => (
                  <ApplicationCard
                    key={app.id}
                    app={app}
                    onMove={(status) => moveMutation.mutate({ appId: app.id, status })}
                  />
                ))}
                {byStage(stage.key).length === 0 && (
                  <p className="text-center text-xs text-muted-foreground pt-6">Empty</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
