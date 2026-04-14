'use client';

import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { hrJobsApi } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

const jobSchema = z.object({
  title:            z.string().min(2, 'Title is required').max(255),
  company_name:     z.string().min(1, 'Company name is required').max(255),
  description:      z.string().min(10, 'Description must be at least 10 characters'),
  skills_raw:       z.string().min(1, 'Add at least one required skill'),
  location:         z.string().max(255).optional().or(z.literal('')),
  employment_type:  z.enum(['FULL_TIME', 'PART_TIME', 'CONTRACT', 'INTERNSHIP']),
  min_experience:   z.coerce.number().min(0).max(50).optional().or(z.literal('')),
  max_experience:   z.coerce.number().min(0).max(50).optional().or(z.literal('')),
  min_salary:       z.coerce.number().min(0).optional().or(z.literal('')),
  max_salary:       z.coerce.number().min(0).optional().or(z.literal('')),
});

type JobFormValues = z.infer<typeof jobSchema>;

const EMPLOYMENT_TYPE_LABELS: Record<string, string> = {
  FULL_TIME:   'Full Time',
  PART_TIME:   'Part Time',
  CONTRACT:    'Contract',
  INTERNSHIP:  'Internship',
};

export default function HrNewJobPage() {
  const router = useRouter();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<JobFormValues>({
    resolver: zodResolver(jobSchema),
    defaultValues: { employment_type: 'FULL_TIME' },
  });

  async function onSubmit(values: JobFormValues) {
    try {
      const required_skills = values.skills_raw
        .split(',').map((s) => s.trim()).filter(Boolean);

      await hrJobsApi.create({
        title:           values.title,
        company_name:    values.company_name,
        description:     values.description,
        required_skills,
        employment_type: values.employment_type,
        location:        values.location || null,
        min_experience:  values.min_experience !== '' ? Number(values.min_experience) : null,
        max_experience:  values.max_experience !== '' ? Number(values.max_experience) : null,
        min_salary:      values.min_salary !== '' ? Number(values.min_salary) : null,
        max_salary:      values.max_salary !== '' ? Number(values.max_salary) : null,
      });
      toast.success('Job posted successfully!');
      router.push('/hr/jobs');
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail ?? 'Failed to post job. Please try again.');
    }
  }

  const field = 'rounded-md border border-input bg-background px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2';
  const label = 'text-sm font-medium leading-none mb-1.5 block';
  const errMsg = 'text-xs text-destructive mt-1';

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Post a New Job</h1>
        <p className="text-muted-foreground">Fill in the details below. Required skills power the smart candidate matching.</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Basic Info */}
        <Card>
          <CardHeader><CardTitle className="text-base">Basic Information</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className={label}>Job Title *</label>
                <input {...register('title')} className={field} placeholder="Senior Frontend Engineer" />
                {errors.title && <p className={errMsg}>{errors.title.message}</p>}
              </div>
              <div>
                <label className={label}>Company Name *</label>
                <input {...register('company_name')} className={field} placeholder="Acme Corp" />
                {errors.company_name && <p className={errMsg}>{errors.company_name.message}</p>}
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className={label}>Location</label>
                <input {...register('location')} className={field} placeholder="San Francisco, CA or Remote" />
              </div>
              <div>
                <label className={label}>Employment Type *</label>
                <select {...register('employment_type')} className={field}>
                  {Object.entries(EMPLOYMENT_TYPE_LABELS).map(([val, label]) => (
                    <option key={val} value={val}>{label}</option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className={label}>Description *</label>
              <textarea
                {...register('description')}
                rows={6}
                className={`${field} resize-none`}
                placeholder="Describe the role, responsibilities, team culture, and what success looks like in this position..."
              />
              {errors.description && <p className={errMsg}>{errors.description.message}</p>}
            </div>
          </CardContent>
        </Card>

        {/* Skills & Experience */}
        <Card>
          <CardHeader><CardTitle className="text-base">Skills &amp; Experience</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className={label}>Required Skills * <span className="text-muted-foreground font-normal">(comma-separated)</span></label>
              <input
                {...register('skills_raw')}
                className={field}
                placeholder="React, TypeScript, Node.js, PostgreSQL"
              />
              {errors.skills_raw && <p className={errMsg}>{errors.skills_raw.message}</p>}
              <p className="text-xs text-muted-foreground mt-1">These skills are used to compute candidate match scores.</p>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className={label}>Min Experience (years)</label>
                <input {...register('min_experience')} type="number" min={0} max={50} className={field} placeholder="3" />
                {errors.min_experience && <p className={errMsg}>{errors.min_experience.message}</p>}
              </div>
              <div>
                <label className={label}>Max Experience (years)</label>
                <input {...register('max_experience')} type="number" min={0} max={50} className={field} placeholder="7" />
                {errors.max_experience && <p className={errMsg}>{errors.max_experience.message}</p>}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Compensation */}
        <Card>
          <CardHeader><CardTitle className="text-base">Compensation</CardTitle></CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className={label}>Min Salary (USD/yr)</label>
                <input {...register('min_salary')} type="number" min={0} className={field} placeholder="120000" />
              </div>
              <div>
                <label className={label}>Max Salary (USD/yr)</label>
                <input {...register('max_salary')} type="number" min={0} className={field} placeholder="160000" />
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="flex gap-3">
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Posting…' : 'Post Job'}
          </Button>
          <Button type="button" variant="outline" onClick={() => router.back()}>
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}
