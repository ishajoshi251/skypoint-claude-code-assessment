import { Briefcase, Users, Send, TrendingUp } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

const STAT_CARDS = [
  { label: 'Active Jobs', value: '—', icon: Briefcase, desc: 'Open positions posted by you' },
  { label: 'Candidates Ranked', value: '—', icon: Users, desc: 'Matched via smart search' },
  { label: 'Invites Sent', value: '—', icon: Send, desc: 'Personalised outreach' },
  { label: 'Avg. Match Score', value: '—', icon: TrendingUp, desc: 'Across all ranked candidates' },
];

export default function HrDashboard() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">HR Dashboard</h1>
        <p className="text-muted-foreground">Manage your jobs, find great candidates, and track your pipeline.</p>
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {STAT_CARDS.map(({ label, value, icon: Icon, desc }) => (
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
            <a href="/hr/jobs/new"
              className="inline-flex items-center gap-2 rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 transition-colors">
              Create Job →
            </a>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Smart Candidate Search</CardTitle>
            <CardDescription>Paste a job description to instantly find and rank the best-fit candidates.</CardDescription>
          </CardHeader>
          <CardContent>
            <a href="/hr/candidates"
              className="inline-flex items-center gap-2 rounded-md border border-brand-600 px-4 py-2 text-sm font-medium text-brand-600 hover:bg-brand-50 transition-colors">
              Search Candidates →
            </a>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
