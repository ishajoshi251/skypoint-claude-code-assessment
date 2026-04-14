'use client';

import { useQuery } from '@tanstack/react-query';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import {
  Briefcase,
  Users,
  TrendingUp,
  CheckCircle,
  Activity,
  Star,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { analyticsApi, type JobFunnelRow } from '@/lib/api';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Stat card
// ---------------------------------------------------------------------------
function StatCard({
  label,
  value,
  desc,
  icon: Icon,
  accent,
}: {
  label: string;
  value: string;
  desc: string;
  icon: React.ElementType;
  accent?: string;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium">{label}</CardTitle>
        <Icon className={cn('h-4 w-4', accent ?? 'text-muted-foreground')} />
      </CardHeader>
      <CardContent>
        <div className={cn('text-2xl font-bold', accent)}>{value}</div>
        <p className="text-xs text-muted-foreground mt-1">{desc}</p>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Per-job funnel inline bars
// ---------------------------------------------------------------------------
const STAGE_COLORS: Record<string, string> = {
  applied: '#3b82f6',
  shortlisted: '#eab308',
  interview: '#f97316',
  offered: '#a855f7',
  hired: '#22c55e',
};

function FunnelRow({ row }: { row: JobFunnelRow }) {
  const stages = [
    { key: 'applied', label: 'Applied', value: row.applied },
    { key: 'shortlisted', label: 'Shortlisted', value: row.shortlisted },
    { key: 'interview', label: 'Interview', value: row.interview },
    { key: 'offered', label: 'Offered', value: row.offered },
    { key: 'hired', label: 'Hired', value: row.hired },
  ];
  const max = Math.max(row.total, 1);

  return (
    <div className="py-3 border-b last:border-0 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <span className="font-medium text-sm truncate block">{row.job_title}</span>
          <span className="text-xs text-muted-foreground">{row.company}</span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {row.rejected > 0 && (
            <span className="text-xs text-red-500">{row.rejected} rejected</span>
          )}
          <span
            className={cn(
              'rounded-full px-2 py-0.5 text-[10px] font-semibold',
              row.status === 'OPEN'
                ? 'bg-green-100 text-green-700'
                : 'bg-slate-100 text-slate-500',
            )}
          >
            {row.status}
          </span>
          <span className="text-xs text-muted-foreground">{row.total} total</span>
        </div>
      </div>
      <div className="space-y-1">
        {stages.map((s) => (
          <div key={s.key} className="flex items-center gap-2">
            <span className="w-20 text-[11px] text-muted-foreground shrink-0">{s.label}</span>
            <div className="flex-1 h-4 rounded bg-muted overflow-hidden">
              <div
                className="h-full rounded transition-all duration-300"
                style={{
                  width: `${(s.value / max) * 100}%`,
                  backgroundColor: STAGE_COLORS[s.key],
                  minWidth: s.value > 0 ? '4px' : '0',
                }}
              />
            </div>
            <span className="w-5 text-right text-[11px] font-medium">{s.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Skill demand chart colours
// ---------------------------------------------------------------------------
const SKILL_PALETTE = [
  '#6366f1', '#8b5cf6', '#ec4899', '#f97316', '#eab308',
  '#22c55e', '#14b8a6', '#3b82f6', '#f43f5e', '#a855f7',
];

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function HrAnalyticsPage() {
  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['hr', 'analytics', 'summary'],
    queryFn: () => analyticsApi.summary().then((r) => r.data),
  });

  const { data: funnel, isLoading: funnelLoading } = useQuery({
    queryKey: ['hr', 'analytics', 'funnel'],
    queryFn: () => analyticsApi.funnel().then((r) => r.data),
  });

  const { data: skills, isLoading: skillsLoading } = useQuery({
    queryKey: ['hr', 'analytics', 'skills'],
    queryFn: () => analyticsApi.skills().then((r) => r.data),
  });

  const STATS = [
    {
      label: 'Total Jobs Posted',
      value: summaryLoading ? '—' : String(summary?.total_jobs ?? 0),
      desc: `${summary?.open_jobs ?? 0} currently open`,
      icon: Briefcase,
    },
    {
      label: 'Total Applications',
      value: summaryLoading ? '—' : String(summary?.total_applications ?? 0),
      desc: `${summary?.active_pipeline ?? 0} active in pipeline`,
      icon: Users,
    },
    {
      label: 'Avg Match Score',
      value:
        summaryLoading || summary?.avg_match_score == null
          ? '—'
          : `${summary.avg_match_score}%`,
      desc: 'Across all applications',
      icon: Star,
      accent: 'text-brand-600',
    },
    {
      label: 'Candidates Hired',
      value: summaryLoading ? '—' : String(summary?.hired_count ?? 0),
      desc: 'Successfully placed',
      icon: CheckCircle,
      accent: 'text-green-600',
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Analytics</h1>
        <p className="text-muted-foreground">
          Hiring funnel, pipeline health, and skill demand across your jobs.
        </p>
      </div>

      {/* Summary stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {STATS.map(({ label, value, desc, icon, accent }) => (
          <StatCard key={label} label={label} value={value} desc={desc} icon={icon} accent={accent} />
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        {/* Hiring funnel — 3/5 width */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-brand-600" />
              Hiring Funnel
            </CardTitle>
            <CardDescription>Applications by stage for each of your jobs.</CardDescription>
          </CardHeader>
          <CardContent>
            {funnelLoading && (
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-16 rounded animate-pulse bg-muted" />
                ))}
              </div>
            )}
            {!funnelLoading && (!funnel || funnel.length === 0) && (
              <div className="rounded-lg border border-dashed p-10 text-center text-muted-foreground text-sm">
                No jobs posted yet. Post a job to see funnel data.
              </div>
            )}
            {!funnelLoading && funnel && funnel.length > 0 && (
              <div>
                {funnel.map((row) => (
                  <FunnelRow key={row.job_id} row={row} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Skill demand — 2/5 width */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-brand-600" />
              Skill Demand
            </CardTitle>
            <CardDescription>Most requested skills across all open jobs.</CardDescription>
          </CardHeader>
          <CardContent>
            {skillsLoading && <div className="h-64 rounded animate-pulse bg-muted" />}
            {!skillsLoading && (!skills || skills.length === 0) && (
              <div className="rounded-lg border border-dashed p-10 text-center text-muted-foreground text-sm">
                No open jobs with required skills found.
              </div>
            )}
            {!skillsLoading && skills && skills.length > 0 && (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart
                  data={skills.slice(0, 12)}
                  layout="vertical"
                  margin={{ top: 0, right: 16, left: 0, bottom: 0 }}
                >
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="skill" width={90} tick={{ fontSize: 11 }} />
                  <Tooltip
                    formatter={(v) => [`${v} job${Number(v) !== 1 ? 's' : ''}`, 'Demand']}
                    contentStyle={{ fontSize: 12 }}
                  />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                    {skills.slice(0, 12).map((_, i) => (
                      <Cell key={i} fill={SKILL_PALETTE[i % SKILL_PALETTE.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Pipeline summary table */}
      {funnel && funnel.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Pipeline Summary</CardTitle>
            <CardDescription>Quick overview of all your jobs at a glance.</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/40">
                    {['Job', 'Status', 'Applied', 'Shortlisted', 'Interview', 'Offered', 'Hired', 'Rejected'].map(
                      (h) => (
                        <th
                          key={h}
                          className="px-4 py-2.5 text-left text-xs font-semibold text-muted-foreground"
                        >
                          {h}
                        </th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody>
                  {funnel.map((row) => (
                    <tr key={row.job_id} className="border-b last:border-0 hover:bg-muted/20">
                      <td className="px-4 py-2.5">
                        <div className="font-medium">{row.job_title}</div>
                        <div className="text-xs text-muted-foreground">{row.company}</div>
                      </td>
                      <td className="px-4 py-2.5">
                        <span
                          className={cn(
                            'rounded-full px-2 py-0.5 text-[10px] font-semibold',
                            row.status === 'OPEN'
                              ? 'bg-green-100 text-green-700'
                              : 'bg-slate-100 text-slate-500',
                          )}
                        >
                          {row.status}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 tabular-nums">{row.applied}</td>
                      <td className="px-4 py-2.5 tabular-nums">{row.shortlisted}</td>
                      <td className="px-4 py-2.5 tabular-nums">{row.interview}</td>
                      <td className="px-4 py-2.5 tabular-nums">{row.offered}</td>
                      <td className="px-4 py-2.5 tabular-nums text-green-600 font-medium">
                        {row.hired}
                      </td>
                      <td className="px-4 py-2.5 tabular-nums text-red-500">{row.rejected}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
