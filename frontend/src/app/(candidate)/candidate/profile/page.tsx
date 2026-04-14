'use client';

import { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Upload, X, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { profileApi, type CandidateProfileOut } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

// ---------------------------------------------------------------------------
// Profile completeness
// ---------------------------------------------------------------------------

const COMPLETENESS_FIELDS: { key: keyof CandidateProfileOut; label: string; points: number }[] = [
  { key: 'full_name',         label: 'Full name',        points: 15 },
  { key: 'headline',          label: 'Headline',         points: 10 },
  { key: 'bio',               label: 'Bio',              points: 10 },
  { key: 'skills',            label: 'Skills',           points: 20 },
  { key: 'years_experience',  label: 'Experience years', points: 10 },
  { key: 'location',          label: 'Location',         points: 5  },
  { key: 'resume_id',         label: 'Resume uploaded',  points: 25 },
  { key: 'expected_salary',   label: 'Expected salary',  points: 5  },
];

function computeCompleteness(profile: CandidateProfileOut) {
  let score = 0;
  const missing: string[] = [];
  for (const f of COMPLETENESS_FIELDS) {
    const val = profile[f.key];
    const filled = val !== null && val !== undefined && (Array.isArray(val) ? val.length > 0 : true);
    if (filled) score += f.points;
    else missing.push(`${f.label} (+${f.points}%)`);
  }
  return { score, missing };
}

function CompletenessBar({ profile }: { profile: CandidateProfileOut }) {
  const { score, missing } = computeCompleteness(profile);
  const color = score >= 80 ? 'bg-green-500' : score >= 50 ? 'bg-amber-500' : 'bg-brand-600';
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Profile Strength</CardTitle>
        <CardDescription>A stronger profile improves your match scores.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between text-sm font-medium">
          <span>{score}% complete</span>
          {score === 100 && <span className="text-green-600 flex items-center gap-1"><CheckCircle2 className="h-4 w-4" /> Complete!</span>}
        </div>
        <div className="h-2.5 w-full rounded-full bg-muted overflow-hidden">
          <div className={`h-full rounded-full transition-all duration-500 ${color}`} style={{ width: `${score}%` }} />
        </div>
        {missing.length > 0 && (
          <div className="text-xs text-muted-foreground space-y-0.5">
            <p className="font-medium text-foreground">To improve your score, add:</p>
            {missing.map((m) => <p key={m}>• {m}</p>)}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Resume uploader
// ---------------------------------------------------------------------------

function ResumeUploader({ resumeId, onUploaded }: { resumeId: number | null; onUploaded: () => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  async function handleFile(file: File) {
    setUploading(true);
    try {
      await profileApi.uploadResume(file);
      toast.success('Resume uploaded and profile updated!');
      onUploaded();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail ?? 'Upload failed. Use PDF or DOCX under 10 MB.');
    } finally {
      setUploading(false);
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Resume</CardTitle>
        <CardDescription>Upload PDF or DOCX — skills and experience will be auto-extracted.</CardDescription>
      </CardHeader>
      <CardContent>
        <div
          onDrop={onDrop}
          onDragOver={(e) => e.preventDefault()}
          onClick={() => inputRef.current?.click()}
          className="cursor-pointer rounded-lg border-2 border-dashed border-muted-foreground/30 p-8 text-center hover:border-brand-400 hover:bg-brand-50/40 dark:hover:bg-brand-900/10 transition-colors"
        >
          <Upload className="mx-auto h-8 w-8 text-muted-foreground mb-2" />
          {resumeId ? (
            <p className="text-sm font-medium text-green-600">Resume on file — drop a new one to replace</p>
          ) : (
            <p className="text-sm text-muted-foreground">Drag & drop or <span className="text-brand-600 font-medium">browse</span></p>
          )}
          <p className="text-xs text-muted-foreground mt-1">PDF or DOCX, max 10 MB</p>
        </div>
        <input ref={inputRef} type="file" accept=".pdf,.docx,.doc" className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }} />
        {uploading && <p className="text-sm text-muted-foreground mt-2 text-center animate-pulse">Uploading & parsing…</p>}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Profile form schema
// ---------------------------------------------------------------------------

const profileSchema = z.object({
  full_name:          z.string().max(255).optional().or(z.literal('')),
  headline:           z.string().max(255).optional().or(z.literal('')),
  location:           z.string().max(255).optional().or(z.literal('')),
  bio:                z.string().max(2000).optional().or(z.literal('')),
  years_experience:   z.coerce.number().min(0).max(50).optional().or(z.literal('')),
  expected_salary:    z.coerce.number().min(0).optional().or(z.literal('')),
  notice_period_days: z.coerce.number().min(0).max(365).optional().or(z.literal('')),
  skills_raw:         z.string().optional(),
});

type ProfileFormValues = z.infer<typeof profileSchema>;

function ProfileForm({ profile, onSaved }: { profile: CandidateProfileOut; onSaved: () => void }) {
  const { register, handleSubmit, formState: { errors, isSubmitting, isDirty } } = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      full_name:          profile.full_name ?? '',
      headline:           profile.headline ?? '',
      location:           profile.location ?? '',
      bio:                profile.bio ?? '',
      years_experience:   profile.years_experience ?? '',
      expected_salary:    profile.expected_salary ?? '',
      notice_period_days: profile.notice_period_days ?? '',
      skills_raw:         (profile.skills ?? []).join(', '),
    },
  });

  async function onSubmit(values: ProfileFormValues) {
    const skills = values.skills_raw
      ? values.skills_raw.split(',').map((s) => s.trim()).filter(Boolean)
      : undefined;

    await profileApi.update({
      full_name:          values.full_name || null,
      headline:           values.headline || null,
      location:           values.location || null,
      bio:                values.bio || null,
      years_experience:   values.years_experience !== '' ? Number(values.years_experience) : null,
      expected_salary:    values.expected_salary !== '' ? Number(values.expected_salary) : null,
      notice_period_days: values.notice_period_days !== '' ? Number(values.notice_period_days) : null,
      skills,
    });
    toast.success('Profile saved!');
    onSaved();
  }

  const field = 'rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 w-full';
  const label = 'text-sm font-medium leading-none mb-1.5 block';
  const err = 'text-xs text-destructive mt-1';

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className={label}>Full Name</label>
          <input {...register('full_name')} className={field} placeholder="Jane Doe" />
          {errors.full_name && <p className={err}>{errors.full_name.message}</p>}
        </div>
        <div>
          <label className={label}>Headline</label>
          <input {...register('headline')} className={field} placeholder="Senior React Developer" />
          {errors.headline && <p className={err}>{errors.headline.message}</p>}
        </div>
        <div>
          <label className={label}>Location</label>
          <input {...register('location')} className={field} placeholder="San Francisco, CA" />
        </div>
        <div>
          <label className={label}>Years of Experience</label>
          <input {...register('years_experience')} type="number" min={0} max={50} step={0.5} className={field} placeholder="5" />
          {errors.years_experience && <p className={err}>{errors.years_experience.message}</p>}
        </div>
        <div>
          <label className={label}>Expected Salary (USD/yr)</label>
          <input {...register('expected_salary')} type="number" min={0} className={field} placeholder="120000" />
        </div>
        <div>
          <label className={label}>Notice Period (days)</label>
          <input {...register('notice_period_days')} type="number" min={0} max={365} className={field} placeholder="30" />
        </div>
      </div>

      <div>
        <label className={label}>Skills <span className="text-muted-foreground font-normal">(comma-separated)</span></label>
        <input {...register('skills_raw')} className={field} placeholder="React, TypeScript, Node.js, PostgreSQL" />
      </div>

      <div>
        <label className={label}>Bio</label>
        <textarea {...register('bio')} rows={4} className={`${field} resize-none`}
          placeholder="Tell us about yourself, your experience, and what you're looking for." />
        {errors.bio && <p className={err}>{errors.bio.message}</p>}
      </div>

      <Button type="submit" disabled={isSubmitting || !isDirty}>
        {isSubmitting ? 'Saving…' : 'Save Profile'}
      </Button>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function CandidateProfilePage() {
  const qc = useQueryClient();

  const { data: profile, isLoading } = useQuery({
    queryKey: ['profile', 'me'],
    queryFn: () => profileApi.get().then((r) => r.data),
  });

  function refetch() {
    qc.invalidateQueries({ queryKey: ['profile', 'me'] });
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-7 w-40 bg-muted rounded animate-pulse" />
        <div className="h-32 bg-muted rounded-xl animate-pulse" />
        <div className="h-64 bg-muted rounded-xl animate-pulse" />
      </div>
    );
  }

  if (!profile) return null;

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">My Profile</h1>
        <p className="text-muted-foreground">Keep your profile up to date to improve match scores.</p>
      </div>

      <CompletenessBar profile={profile} />
      <ResumeUploader resumeId={profile.resume_id} onUploaded={refetch} />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Profile Details</CardTitle>
        </CardHeader>
        <CardContent>
          <ProfileForm profile={profile} onSaved={refetch} />
        </CardContent>
      </Card>
    </div>
  );
}
