'use client';

interface MatchScoreBadgeProps {
  score: number; // 0–100
  size?: 'sm' | 'md' | 'lg';
}

const SIZE = { sm: 44, md: 60, lg: 80 };
const STROKE = { sm: 4, md: 5, lg: 6 };

function scoreColor(score: number) {
  if (score >= 70) return '#22c55e'; // green-500
  if (score >= 45) return '#f59e0b'; // amber-500
  return '#ef4444';                   // red-500
}

export function MatchScoreBadge({ score, size = 'md' }: MatchScoreBadgeProps) {
  const px = SIZE[size];
  const sw = STROKE[size];
  const r = (px - sw) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (Math.min(score, 100) / 100) * circ;
  const color = scoreColor(score);
  const fs = size === 'sm' ? 10 : size === 'md' ? 13 : 18;

  return (
    <svg width={px} height={px} viewBox={`0 0 ${px} ${px}`} className="shrink-0">
      {/* Track */}
      <circle cx={px / 2} cy={px / 2} r={r} fill="none" stroke="#e5e7eb" strokeWidth={sw} />
      {/* Progress */}
      <circle
        cx={px / 2} cy={px / 2} r={r}
        fill="none"
        stroke={color}
        strokeWidth={sw}
        strokeLinecap="round"
        strokeDasharray={circ}
        strokeDashoffset={offset}
        transform={`rotate(-90 ${px / 2} ${px / 2})`}
      />
      {/* Label */}
      <text
        x="50%" y="50%"
        dominantBaseline="middle"
        textAnchor="middle"
        fontSize={fs}
        fontWeight="600"
        fill={color}
      >
        {Math.round(score)}%
      </text>
    </svg>
  );
}
