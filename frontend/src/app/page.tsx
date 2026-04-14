import { redirect } from 'next/navigation';
import { cookies } from 'next/headers';

// Root page — redirect based on session role cookie
export default function RootPage() {
  const cookieStore = cookies();
  const role = cookieStore.get('tb_role')?.value;

  if (role === 'HR') redirect('/hr/dashboard');
  if (role === 'CANDIDATE') redirect('/candidate/dashboard');

  // Not logged in
  redirect('/login');
}
