import { cn } from '@/lib/utils';

interface SkillTagProps {
  skill: string;
  variant?: 'default' | 'matched' | 'missing';
}

export function SkillTag({ skill, variant = 'default' }: SkillTagProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        variant === 'matched' && 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
        variant === 'missing' && 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
        variant === 'default' && 'bg-brand-100 text-brand-800 dark:bg-brand-900/30 dark:text-brand-300',
      )}
    >
      {skill}
    </span>
  );
}
