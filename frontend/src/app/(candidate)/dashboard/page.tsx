import { Briefcase, FileText, Star, TrendingUp } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

const STAT_CARDS = [
  { label: 'Jobs Matched', value: '—', icon: Star, desc: 'Complete your profile to see matches' },
  { label: 'Applications', value: '0', icon: FileText, desc: 'Track your application status' },
  { label: 'Jobs Browsed', value: '0', icon: Briefcase, desc: 'Jobs you\'ve viewed' },
  { label: 'Profile Strength', value: '10%', icon: TrendingUp, desc: 'Upload a resume to boost' },
];

export default function CandidateDashboard() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Welcome back</h1>
        <p className="text-muted-foreground">Here&apos;s a snapshot of your job search activity.</p>
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

      {/* CTA */}
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
    </div>
  );
}
