'use client';

import { useState } from 'react';
import { MapPin, Clock, DollarSign, Building2 } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { MatchScoreBadge } from './match-score-badge';
import { SkillTag } from './skill-tag';
import type { JobOut, MatchScoreOut } from '@/lib/api';
import { applicationsApi } from '@/lib/api';
import { useQueryClient } from '@tanstack/react-query';

interface JobCardProps {
  job: JobOut;
  matchScore?: MatchScoreOut;
  alreadyApplied?: boolean;
}

function formatSalary(min: string | null, max: string | null) {
  if (!min && !max) return null;
  const fmt = (v: string) => `$${Number(v).toLocaleString()}`;
  if (min && max) return `${fmt(min)} – ${fmt(max)}`;
  if (min) return `From ${fmt(min)}`;
  return `Up to ${fmt(max!)}`;
}

function formatEmploymentType(et: string) {
  return et.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export function JobCard({ job, matchScore, alreadyApplied = false }: JobCardProps) {
  const [applied, setApplied] = useState(alreadyApplied);
  const [applying, setApplying] = useState(false);
  const qc = useQueryClient();

  async function handleApply() {
    setApplying(true);
    try {
      await applicationsApi.apply(job.id);
      setApplied(true);
      toast.success('Application submitted!');
      qc.invalidateQueries({ queryKey: ['applications', 'mine'] });
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      if (detail?.includes('already applied')) {
        setApplied(true);
        toast.info('You have already applied to this job.');
      } else {
        toast.error('Failed to apply. Please try again.');
      }
    } finally {
      setApplying(false);
    }
  }

  const salary = formatSalary(job.min_salary, job.max_salary);

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <h3 className="font-semibold text-base leading-tight truncate">{job.title}</h3>
            <div className="mt-1 flex items-center gap-1.5 text-sm text-muted-foreground">
              <Building2 className="h-3.5 w-3.5 shrink-0" />
              <span className="truncate">{job.company.name}</span>
            </div>
          </div>
          {matchScore !== undefined && (
            <MatchScoreBadge score={matchScore.total} size="md" />
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Meta row */}
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
          {job.location && (
            <span className="flex items-center gap-1">
              <MapPin className="h-3 w-3" /> {job.location}
            </span>
          )}
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" /> {formatEmploymentType(job.employment_type)}
          </span>
          {salary && (
            <span className="flex items-center gap-1">
              <DollarSign className="h-3 w-3" /> {salary}
            </span>
          )}
          {(job.min_experience !== null || job.max_experience !== null) && (
            <span>
              {job.min_experience ?? 0}–{job.max_experience ?? '∞'} yrs exp
            </span>
          )}
        </div>

        {/* Skills */}
        {job.required_skills.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {job.required_skills.slice(0, 6).map((s) => {
              const variant = matchScore
                ? matchScore.matched_skills.includes(s)
                  ? 'matched'
                  : matchScore.missing_skills.includes(s)
                  ? 'missing'
                  : 'default'
                : 'default';
              return <SkillTag key={s} skill={s} variant={variant} />;
            })}
            {job.required_skills.length > 6 && (
              <span className="text-xs text-muted-foreground self-center">
                +{job.required_skills.length - 6} more
              </span>
            )}
          </div>
        )}

        {/* Score breakdown (when score available) */}
        {matchScore && matchScore.total > 0 && (
          <div className="rounded-md bg-muted/50 px-3 py-2 text-xs space-y-1">
            <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-muted-foreground">
              <span>Skills {Math.round(matchScore.skill_overlap)}%</span>
              <span>Semantic {Math.round(matchScore.semantic)}%</span>
              <span>Experience {Math.round(matchScore.experience_fit)}%</span>
              {matchScore.location_fit > 0 && <span>Location {Math.round(matchScore.location_fit)}%</span>}
            </div>
            {matchScore.missing_skills.length > 0 && (
              <p className="text-red-600 dark:text-red-400">
                Missing: {matchScore.missing_skills.slice(0, 4).join(', ')}
                {matchScore.missing_skills.length > 4 && ` +${matchScore.missing_skills.length - 4}`}
              </p>
            )}
          </div>
        )}

        {/* Description preview */}
        <p className="text-sm text-muted-foreground line-clamp-2">{job.description}</p>

        {/* Apply */}
        <div className="flex items-center justify-between pt-1">
          <span className="text-xs text-muted-foreground">
            {new Date(job.created_at).toLocaleDateString()}
          </span>
          <Button
            size="sm"
            variant={applied ? 'secondary' : 'default'}
            disabled={applied || applying}
            onClick={handleApply}
          >
            {applied ? 'Applied' : applying ? 'Applying…' : 'Apply Now'}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
