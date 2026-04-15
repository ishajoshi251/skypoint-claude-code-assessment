'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';

import { registerSchema, type RegisterFormValues } from '@/lib/schemas';
import { authApi } from '@/lib/api';
import { setRoleCookie } from '@/lib/auth';
import { useAuthStore } from '@/stores/auth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';

export default function RegisterPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const setAuth = useAuthStore((s) => s.setAuth);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { role: 'CANDIDATE' },
  });

  const selectedRole = watch('role');

  async function onSubmit(values: RegisterFormValues) {
    try {
      const { data } = await authApi.register(values.email, values.password, values.role);
      queryClient.clear();
      setAuth(data.access_token, data.user);
      setRoleCookie(data.user.role);
      toast.success('Account created! Welcome to TalentBridge.');
      router.push(data.user.role === 'HR' ? '/hr/dashboard' : '/candidate/dashboard');
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail ?? 'Registration failed. Please try again.');
    }
  }

  return (
    <Card className="w-full max-w-md shadow-xl">
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl">Create account</CardTitle>
        <CardDescription>Join TalentBridge as a candidate or HR recruiter</CardDescription>
      </CardHeader>

      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        <CardContent className="space-y-4">
          {/* Role picker */}
          <div className="space-y-1.5">
            <Label>I am a…</Label>
            <div className="grid grid-cols-2 gap-3">
              {(['CANDIDATE', 'HR'] as const).map((role) => (
                <label
                  key={role}
                  className={`flex cursor-pointer flex-col items-center rounded-lg border-2 p-4 transition-colors ${
                    selectedRole === role
                      ? 'border-brand-600 bg-brand-50 text-brand-700 dark:bg-brand-900/20 dark:text-brand-300'
                      : 'border-border hover:border-brand-300'
                  }`}
                >
                  <input
                    type="radio"
                    value={role}
                    className="sr-only"
                    {...register('role')}
                  />
                  <span className="text-2xl mb-1">
                    {role === 'CANDIDATE' ? '👤' : '🏢'}
                  </span>
                  <span className="text-sm font-medium">
                    {role === 'CANDIDATE' ? 'Job Seeker' : 'HR / Recruiter'}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Email */}
          <div className="space-y-1.5">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="you@example.com"
              autoComplete="email"
              {...register('email')}
              aria-invalid={!!errors.email}
            />
            {errors.email && (
              <p className="text-xs text-destructive">{errors.email.message}</p>
            )}
          </div>

          {/* Password */}
          <div className="space-y-1.5">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              placeholder="Min 8 chars, 1 uppercase, 1 number"
              autoComplete="new-password"
              {...register('password')}
              aria-invalid={!!errors.password}
            />
            {errors.password && (
              <p className="text-xs text-destructive">{errors.password.message}</p>
            )}
          </div>
        </CardContent>

        <CardFooter className="flex flex-col gap-3">
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            Create account
          </Button>
          <p className="text-center text-sm text-muted-foreground">
            Already have an account?{' '}
            <Link href="/login" className="font-medium text-brand-600 hover:underline">
              Sign in
            </Link>
          </p>
        </CardFooter>
      </form>
    </Card>
  );
}
