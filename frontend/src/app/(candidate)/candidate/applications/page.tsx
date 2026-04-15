'use client';

import { useQuery } from '@tanstack/react-query';
import { FileText, Building2, MapPin, Clock } from 'lucide-react';
import { applicationsApi, type ApplicationOut } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/stores/auth';

const STATUS_CONFIG: Record<ApplicationOut['status'], { label: string; color: string; step: number }> = {
  APPLIED:     { label: 'Applied',     color: 'bg-blue-500',   step: 1 },
  SHORTLISTED: { label: 'Shortlisted', color: 'bg-yellow-500', step: 2 },
  INTERVIEW:   { label: 'Interview',   color: 'bg-orange-500', step: 3 },
  OFFERED:     { label: 'Offered',     color: 'bg-purple-500', step: 4 },
  HIRED:       { label: 'Hired',       color: 'bg-green-500',  step: 5 },
  REJECTED:    { label: 'Rejected',    color: 'bg-red-500',    step: 0 },
};

const PIPELINE_STEPS = ['APPLIED', 'SHORTLISTED', 'INTERVIEW', 'OFFERED', 'HIRED'] as const;

function ApplicationCard({ app }: { app: ApplicationOut }) {
  const cfg = STATUS_CONFIG[app.status];
  const currentStep = cfg.step;
  const isRejected = app.status === 'REJECTED';

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <CardTitle className="text-base truncate">{app.job.title}</CardTitle>
            <div className="mt-1 flex items-center gap-1.5 text-sm text-muted-foreground">
              <Building2 className="h-3.5 w-3.5 shrink-0" />
              <span className="truncate">{app.job.company.name}</span>
              {app.job.location && (
                <>
                  <span>·</span>
                  <MapPin className="h-3.5 w-3.5 shrink-0" />
                  <span className="truncate">{app.job.location}</span>
                </>
              )}
            </div>
          </div>
          <span className={cn('shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium text-white', cfg.color)}>
            {cfg.label}
          </span>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Pipeline tracker */}
        {isRejected ? (
          <p className="text-sm text-red-600 dark:text-red-400">
            This application was not selected for further consideration.
          </p>
        ) : (
          <div className="flex items-center gap-0">
            {PIPELINE_STEPS.map((step, idx) => {
              const stepCfg = STATUS_CONFIG[step];
              const done = stepCfg.step <= currentStep;
              const active = step === app.status;
              return (
                <div key={step} className="flex flex-1 items-center">
                  <div className="flex flex-col items-center gap-1 flex-shrink-0">
                    <div className={cn(
                      'h-3 w-3 rounded-full border-2 transition-colors',
                      done ? 'bg-brand-600 border-brand-600' : 'bg-white border-muted-foreground/30',
                      active && 'ring-2 ring-brand-300',
                    )} />
                    <span className={cn(
                      'text-[10px] font-medium whitespace-nowrap',
                      done ? 'text-brand-600' : 'text-muted-foreground/50',
                    )}>
                      {stepCfg.label}
                    </span>
                  </div>
                  {idx < PIPELINE_STEPS.length - 1 && (
                    <div className={cn(
                      'h-0.5 flex-1 mx-1 -mt-3',
                      stepCfg.step < currentStep ? 'bg-brand-600' : 'bg-muted-foreground/20',
                    )} />
                  )}
                </div>
              );
            })}
          </div>
        )}

        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            Applied {new Date(app.created_at).toLocaleDateString()}
          </span>
          {app.match_score && (
            <span className="font-medium text-brand-600">
              {Math.round(Number(app.match_score))}% match
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function ApplicationSkeleton() {
  return (
    <div className="rounded-xl border bg-card p-5 space-y-3 animate-pulse">
      <div className="h-4 w-1/2 bg-muted rounded" />
      <div className="h-3 w-1/3 bg-muted rounded" />
      <div className="flex gap-2 pt-2">
        {[1,2,3,4,5].map(i => <div key={i} className="h-3 flex-1 bg-muted rounded" />)}
      </div>
    </div>
  );
}

export default function CandidateApplicationsPage() {
  const userId = useAuthStore((s) => s.user?.id);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['applications', 'mine', userId],
    queryFn: () => applicationsApi.mine({ limit: 50 }).then((r) => r.data),
    enabled: !!userId,
  });

  const apps = data?.items ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">My Applications</h1>
        <p className="text-muted-foreground">
          {data ? `${data.total} application${data.total !== 1 ? 's' : ''}` : 'Track your application status'}
        </p>
      </div>

      {isError && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          Failed to load applications. Please refresh.
        </div>
      )}

      {isLoading && (
        <div className="grid gap-4 sm:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => <ApplicationSkeleton key={i} />)}
        </div>
      )}

      {!isLoading && apps.length === 0 && !isError && (
        <div className="flex flex-col items-center gap-4 rounded-lg border border-dashed p-16 text-center">
          <FileText className="h-10 w-10 text-muted-foreground" />
          <div>
            <p className="font-medium">No applications yet</p>
            <p className="text-sm text-muted-foreground mt-1">Browse jobs and hit Apply to get started.</p>
          </div>
          <a
            href="/candidate/jobs"
            className="inline-flex items-center gap-2 rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 transition-colors"
          >
            Browse Jobs →
          </a>
        </div>
      )}

      {!isLoading && apps.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2">
          {apps.map((app) => <ApplicationCard key={app.id} app={app} />)}
        </div>
      )}
    </div>
  );
}
