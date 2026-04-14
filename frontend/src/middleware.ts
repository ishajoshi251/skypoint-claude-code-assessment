import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const PUBLIC_PATHS = ['/login', '/register'];
const HR_PREFIX = '/hr';
const CANDIDATE_PREFIX = '/candidate';

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Pass through public routes and Next.js internals
  if (
    PUBLIC_PATHS.some((p) => pathname.startsWith(p)) ||
    pathname.startsWith('/_next') ||
    pathname.startsWith('/api') ||
    pathname === '/favicon.ico'
  ) {
    return NextResponse.next();
  }

  const role = request.cookies.get('tb_role')?.value;

  // Not authenticated — send to login
  if (!role) {
    const url = request.nextUrl.clone();
    url.pathname = '/login';
    url.searchParams.set('from', pathname);
    return NextResponse.redirect(url);
  }

  // Role-based path enforcement
  if (pathname.startsWith(HR_PREFIX) && role !== 'HR') {
    return NextResponse.redirect(new URL('/candidate/dashboard', request.url));
  }
  if (pathname.startsWith(CANDIDATE_PREFIX) && role !== 'CANDIDATE') {
    return NextResponse.redirect(new URL('/hr/dashboard', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
