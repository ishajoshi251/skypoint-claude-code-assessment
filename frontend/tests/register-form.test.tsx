/**
 * Register form validation tests.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock('@/lib/api', () => ({
  authApi: { register: vi.fn() },
}));

vi.mock('@/lib/auth', () => ({
  setRoleCookie: vi.fn(),
}));

vi.mock('@/stores/auth', () => ({
  useAuthStore: (selector: (s: { setAuth: () => void }) => unknown) =>
    selector({ setAuth: vi.fn() }),
}));

import RegisterPage from '@/app/(auth)/register/page';

describe('RegisterPage — form validation', () => {
  beforeEach(() => vi.clearAllMocks());

  function setup() {
    return { user: userEvent.setup(), ...render(<RegisterPage />) };
  }

  it('renders email, password, and role selector', () => {
    setup();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByText(/job seeker/i)).toBeInTheDocument();
    expect(screen.getByText(/hr \/ recruiter/i)).toBeInTheDocument();
  });

  it('shows error for invalid email', async () => {
    const { user } = setup();
    await user.type(screen.getByLabelText(/email/i), 'bad');
    await user.click(screen.getByRole('button', { name: /create account/i }));
    await waitFor(() => {
      expect(screen.getByText(/enter a valid email address/i)).toBeInTheDocument();
    });
  });

  it('shows error when password is too short', async () => {
    const { user } = setup();
    await user.type(screen.getByLabelText(/email/i), 'x@y.com');
    await user.type(screen.getByLabelText(/password/i), 'short');
    await user.click(screen.getByRole('button', { name: /create account/i }));
    await waitFor(() => {
      expect(screen.getByText(/at least 8 characters/i)).toBeInTheDocument();
    });
  });

  it('shows error when password lacks uppercase', async () => {
    const { user } = setup();
    await user.type(screen.getByLabelText(/email/i), 'x@y.com');
    await user.type(screen.getByLabelText(/password/i), 'alllower1');
    await user.click(screen.getByRole('button', { name: /create account/i }));
    await waitFor(() => {
      expect(screen.getByText(/at least one uppercase letter/i)).toBeInTheDocument();
    });
  });

  it('shows error when password lacks a number', async () => {
    const { user } = setup();
    await user.type(screen.getByLabelText(/email/i), 'x@y.com');
    await user.type(screen.getByLabelText(/password/i), 'NoNumber!');
    await user.click(screen.getByRole('button', { name: /create account/i }));
    await waitFor(() => {
      expect(screen.getByText(/at least one number/i)).toBeInTheDocument();
    });
  });

  it('calls authApi.register with correct args when form is valid', async () => {
    const { authApi } = await import('@/lib/api');
    (authApi.register as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      data: {
        access_token: 'tok',
        user: { id: 2, email: 'new@test.com', role: 'CANDIDATE', is_active: true, created_at: '' },
      },
    });

    const { user } = setup();
    await user.type(screen.getByLabelText(/email/i), 'new@test.com');
    await user.type(screen.getByLabelText(/password/i), 'Valid@123');
    await user.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(authApi.register).toHaveBeenCalledWith('new@test.com', 'Valid@123', 'CANDIDATE');
    });
  });
});
