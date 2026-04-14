'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { toast } from 'sonner';
import {
  LayoutDashboard,
  Briefcase,
  FileText,
  User,
  LogOut,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { authApi } from '@/lib/api';
import { clearRoleCookie } from '@/lib/auth';
import { useAuthStore } from '@/stores/auth';
import { Button } from '@/components/ui/button';

const NAV_ITEMS = [
  { href: '/candidate/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/candidate/jobs', label: 'Browse Jobs', icon: Briefcase },
  { href: '/candidate/applications', label: 'My Applications', icon: FileText },
  { href: '/candidate/profile', label: 'Profile', icon: User },
];

export function NavCandidate() {
  const pathname = usePathname() ?? '';
  const router = useRouter();
  const { user, clearAuth } = useAuthStore();

  async function handleLogout() {
    try {
      await authApi.logout();
    } catch {
      // ignore
    } finally {
      clearAuth();
      clearRoleCookie();
      toast.success('Signed out.');
      router.push('/login');
    }
  }

  return (
    <aside className="flex h-full w-64 flex-col border-r bg-white dark:bg-slate-900">
      {/* Logo */}
      <div className="flex h-16 items-center gap-2 border-b px-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
            className="h-4 w-4 text-white">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
            <circle cx="9" cy="7" r="4" />
            <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
            <path d="M16 3.13a4 4 0 0 1 0 7.75" />
          </svg>
        </div>
        <span className="font-bold text-brand-700 dark:text-brand-300">TalentBridge</span>
      </div>

      {/* Nav links */}
      <nav className="flex-1 space-y-1 p-3">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
              pathname.startsWith(href)
                ? 'bg-brand-50 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300'
                : 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800',
            )}
          >
            <Icon className="h-4 w-4 flex-shrink-0" />
            {label}
          </Link>
        ))}
      </nav>

      {/* User + logout */}
      <div className="border-t p-3">
        <div className="mb-2 px-3 py-1">
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Signed in as</p>
          <p className="truncate text-sm font-medium">{user?.email}</p>
        </div>
        <Button variant="ghost" size="sm" className="w-full justify-start text-slate-600" onClick={handleLogout}>
          <LogOut className="mr-2 h-4 w-4" />
          Sign out
        </Button>
      </div>
    </aside>
  );
}
