/**
 * Auth helpers — cookie management and session utilities.
 *
 * We store a non-sensitive `tb_role` cookie (readable by middleware)
 * alongside the httpOnly `refresh_token` set by the backend.
 * The access token itself lives only in the Zustand store (in memory).
 */

export type UserRole = 'HR' | 'CANDIDATE';

/** Set the role cookie so middleware can gate routes without a DB call. */
export function setRoleCookie(role: UserRole) {
  document.cookie = `tb_role=${role}; path=/; max-age=${7 * 24 * 3600}; samesite=lax`;
}

/** Clear the role cookie on logout. */
export function clearRoleCookie() {
  document.cookie = 'tb_role=; path=/; max-age=0; samesite=lax';
}

/** Read role from cookie (client-side only). */
export function getRoleFromCookie(): UserRole | null {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(/(?:^|;\s*)tb_role=([^;]+)/);
  return (match?.[1] as UserRole) ?? null;
}
