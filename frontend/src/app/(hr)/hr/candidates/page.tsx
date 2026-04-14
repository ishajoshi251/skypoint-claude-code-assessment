'use client';

import { useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Search, Send, ChevronDown, ChevronUp } from 'lucide-react';
import { toast } from 'sonner';
import { hrCandidatesApi, hrInvitesApi, hrJobsApi, type RankedCandidateOut } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { MatchScoreBadge } from '@/components/jobs/match-score-badge';
import { SkillTag } from '@/components/jobs/skill-tag';

// ---------------------------------------------------------------------------
// Candidate result card
// ---------------------------------------------------------------------------

function CandidateCard({
  result,
  selected,
  onToggle,
}: {
  result: RankedCandidateOut;
  selected: boolean;
  onToggle: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const p = result.profile;
  const s = result.score;

  return (
    <Card className={selected ? 'ring-2 ring-brand-500' : ''}>
      <CardHeader className="pb-2">
        <div className="flex items-start gap-3">
          <input
            type="checkbox"
            checked={selected}
            onChange={onToggle}
            className="mt-1 h-4 w-4 rounded border-input accent-brand-600 cursor-pointer"
          />
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between gap-2">
              <div>
                <p className="font-semibold">{p.full_name ?? result.email}</p>
                {p.full_name && <p className="text-xs text-muted-foreground">{result.email}</p>}
                {p.headline && <p className="text-sm text-muted-foreground mt-0.5">{p.headline}</p>}
              </div>
              <MatchScoreBadge score={s.total} size="md" />
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Score breakdown */}
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground rounded-md bg-muted/50 px-3 py-2">
          <span>Skills <strong className="text-foreground">{Math.round(s.skill_overlap)}%</strong></span>
          <span>Semantic <strong className="text-foreground">{Math.round(s.semantic)}%</strong></span>
          <span>Experience <strong className="text-foreground">{Math.round(s.experience_fit)}%</strong></span>
          {s.location_fit > 0 && <span>Location <strong className="text-foreground">{Math.round(s.location_fit)}%</strong></span>}
        </div>

        {/* Skills */}
        {s.matched_skills.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {s.matched_skills.map((sk) => <SkillTag key={sk} skill={sk} variant="matched" />)}
            {s.missing_skills.map((sk) => <SkillTag key={sk} skill={sk} variant="missing" />)}
          </div>
        )}

        {/* Expandable details */}
        <button
          onClick={() => setExpanded((v) => !v)}
          className="flex items-center gap-1 text-xs text-brand-600 hover:underline"
        >
          {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          {expanded ? 'Less detail' : 'More detail'}
        </button>

        {expanded && (
          <div className="space-y-1.5 text-xs text-muted-foreground border-t pt-2">
            {p.location && <p>📍 {p.location}</p>}
            {p.years_experience != null && <p>🕐 {p.years_experience} years experience</p>}
            {p.expected_salary != null && <p>💰 Expecting ${Number(p.expected_salary).toLocaleString()}/yr</p>}
            {p.notice_period_days != null && <p>📅 {p.notice_period_days} day notice period</p>}
            {p.bio && <p className="line-clamp-3 mt-1">{p.bio}</p>}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function HrCandidatesPage() {
  const searchParams = useSearchParams();
  const preselectedJobId = searchParams.get('job_id');

  const [queryText, setQueryText] = useState('');
  const [selectedJobId, setSelectedJobId] = useState<string>(preselectedJobId ?? '');
  const [minScore, setMinScore] = useState(0);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [results, setResults] = useState<RankedCandidateOut[]>([]);
  const [inviteMessage, setInviteMessage] = useState('');
  const [showInvitePanel, setShowInvitePanel] = useState(false);

  const { data: jobsData } = useQuery({
    queryKey: ['hr', 'jobs'],
    queryFn: () => hrJobsApi.list({ limit: 100 }).then((r) => r.data),
  });
  const openJobs = (jobsData?.items ?? []).filter((j) => j.status === 'OPEN');

  const searchMutation = useMutation({
    mutationFn: () =>
      hrCandidatesApi.search({
        job_id: selectedJobId ? Number(selectedJobId) : null,
        query_text: queryText || null,
        min_score: minScore,
        limit: 30,
      }).then((r) => r.data),
    onSuccess: (data) => {
      setResults(data);
      setSelected(new Set());
      if (data.length === 0) toast.info('No candidates matched your criteria.');
    },
    onError: () => toast.error('Search failed. Please try again.'),
  });

  const inviteMutation = useMutation({
    mutationFn: () =>
      hrInvitesApi.bulkInvite(
        Number(selectedJobId),
        Array.from(selected),
        inviteMessage || undefined,
      ),
    onSuccess: () => {
      toast.success(`Invite${selected.size > 1 ? 's' : ''} sent via MailHog!`);
      setSelected(new Set());
      setShowInvitePanel(false);
      setInviteMessage('');
    },
    onError: () => toast.error('Failed to send invites.'),
  });

  function toggleSelect(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  function toggleAll() {
    if (selected.size === results.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(results.map((r) => r.candidate_id)));
    }
  }

  const canInvite = selected.size > 0 && !!selectedJobId;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Find Candidates</h1>
        <p className="text-muted-foreground">Paste a job description to instantly rank the best-fit candidates.</p>
      </div>

      {/* Search panel */}
      <Card>
        <CardContent className="pt-5 space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="text-sm font-medium mb-1.5 block">Match against a Job</label>
              <select
                value={selectedJobId}
                onChange={(e) => setSelectedJobId(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="">— Select a job (optional) —</option>
                {openJobs.map((j) => (
                  <option key={j.id} value={j.id}>{j.title} · {j.company.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium mb-1.5 block">Min Match Score: <strong>{minScore}%</strong></label>
              <input
                type="range" min={0} max={90} step={5}
                value={minScore}
                onChange={(e) => setMinScore(Number(e.target.value))}
                className="w-full accent-brand-600"
              />
            </div>
          </div>

          <div>
            <label className="text-sm font-medium mb-1.5 block">Job Description / Search Query</label>
            <textarea
              rows={5}
              value={queryText}
              onChange={(e) => setQueryText(e.target.value)}
              placeholder="Paste a job description or describe what you're looking for — e.g. 'Senior React developer with GraphQL and 4+ years experience'..."
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>

          <Button
            onClick={() => searchMutation.mutate()}
            disabled={searchMutation.isPending || (!queryText && !selectedJobId)}
            className="gap-2"
          >
            <Search className="h-4 w-4" />
            {searchMutation.isPending ? 'Ranking…' : 'Rank Candidates'}
          </Button>
        </CardContent>
      </Card>

      {/* Results */}
      {results.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <p className="font-semibold">{results.length} candidates ranked</p>
              <button onClick={toggleAll} className="text-sm text-brand-600 hover:underline">
                {selected.size === results.length ? 'Deselect all' : 'Select all'}
              </button>
            </div>

            {canInvite && (
              <Button
                variant="outline"
                className="gap-2"
                onClick={() => setShowInvitePanel((v) => !v)}
              >
                <Send className="h-4 w-4" />
                Invite {selected.size} candidate{selected.size !== 1 ? 's' : ''}
              </Button>
            )}
          </div>

          {/* Invite panel */}
          {showInvitePanel && (
            <Card className="border-brand-200 bg-brand-50/50 dark:bg-brand-900/10">
              <CardContent className="pt-4 space-y-3">
                <p className="text-sm font-medium">Personalised invite message <span className="text-muted-foreground font-normal">(optional)</span></p>
                <textarea
                  rows={3}
                  value={inviteMessage}
                  onChange={(e) => setInviteMessage(e.target.value)}
                  placeholder="Add a personal note — the email will also mention their matched skills automatically."
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
                />
                <div className="flex gap-2">
                  <Button
                    onClick={() => inviteMutation.mutate()}
                    disabled={inviteMutation.isPending}
                    className="gap-2"
                  >
                    <Send className="h-4 w-4" />
                    {inviteMutation.isPending ? 'Sending…' : `Send ${selected.size} Invite${selected.size !== 1 ? 's' : ''}`}
                  </Button>
                  <Button variant="ghost" onClick={() => setShowInvitePanel(false)}>Cancel</Button>
                </div>
              </CardContent>
            </Card>
          )}

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {results.map((r) => (
              <CandidateCard
                key={r.candidate_id}
                result={r}
                selected={selected.has(r.candidate_id)}
                onToggle={() => toggleSelect(r.candidate_id)}
              />
            ))}
          </div>
        </div>
      )}

      {searchMutation.isSuccess && results.length === 0 && (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed p-12 text-center text-muted-foreground">
          <Search className="h-8 w-8" />
          <p>No candidates matched your criteria. Try lowering the min score or broadening your query.</p>
        </div>
      )}
    </div>
  );
}
