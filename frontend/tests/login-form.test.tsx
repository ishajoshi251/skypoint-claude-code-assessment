/**
 * Login form validation tests.
 * Verifies that Zod + React Hook Form enforce rules before any API call.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// ---- Mocks ----------------------------------------------------------------
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => ({ get: vi.fn().mockReturnValue(null) }),
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock('@/lib/api', () => ({
  authApi: {
    login: vi.fn(),
  },
}));

vi.mock('@/lib/auth', () => ({
  setRoleCookie: vi.fn(),
}));

vi.mock('@/stores/auth', () => ({
  useAuthStore: (selector: (s: { setAuth: () => void }) => unknown) =>
    selector({ setAuth: vi.fn() }),
}));
// ---------------------------------------------------------------------------

import LoginPage from '@/app/(auth)/login/page';

describe('LoginPage — form validation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  function setup() {
    const user = userEvent.setup();
    render(<LoginPage />);
    return { user };
  }

  it('renders email and password fields', () => {
    setup();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it('shows "Enter a valid email address" when email is invalid', async () => {
    const { user } = setup();
    const emailInput = screen.getByLabelText(/email/i);
    await user.type(emailInput, 'not-an-email');
    await user.type(screen.getByLabelText(/password/i), 'Hr@12345');
    await user.click(screen.getByRole('button', { name: /sign in/i }));
    await waitFor(() => {
      expect(screen.getByText(/enter a valid email address/i)).toBeInTheDocument();
    });
  });

  it('shows error when password is empty on submit', async () => {
    const { user } = setup();
    await user.type(screen.getByLabelText(/email/i), 'test@example.com');
    await user.click(screen.getByRole('button', { name: /sign in/i }));
    await waitFor(() => {
      expect(screen.getByText(/password is required/i)).toBeInTheDocument();
    });
  });

  it('does not call authApi.login when form is invalid', async () => {
    const { authApi } = await import('@/lib/api');
    const { user } = setup();
    // Submit with empty fields
    await user.click(screen.getByRole('button', { name: /sign in/i }));
    await waitFor(() => {
      expect(authApi.login).not.toHaveBeenCalled();
    });
  });

  it('shows no errors when form is valid and submits', async () => {
    const { authApi } = await import('@/lib/api');
    (authApi.login as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      data: {
        access_token: 'tok',
        user: { id: 1, email: 'hr@test.com', role: 'HR', is_active: true, created_at: '' },
      },
    });

    const { user } = setup();
    await user.type(screen.getByLabelText(/email/i), 'hr@test.com');
    await user.type(screen.getByLabelText(/password/i), 'Hr@12345');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(authApi.login).toHaveBeenCalledWith('hr@test.com', 'Hr@12345');
    });
    expect(screen.queryByText(/enter a valid email/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/password is required/i)).not.toBeInTheDocument();
  });
});
