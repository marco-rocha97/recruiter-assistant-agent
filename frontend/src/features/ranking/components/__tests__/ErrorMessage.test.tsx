import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ApiError } from '../../types';
import { ErrorMessage } from '../ErrorMessage';

const testError: ApiError = {
  error_code: 'invalid_jd',
  message: 'Job description is too short.',
};

describe('ErrorMessage', () => {
  it('renders the error message text', () => {
    render(<ErrorMessage error={testError} onReset={() => {}} />);
    expect(screen.getByText('Job description is too short.')).toBeInTheDocument();
  });

  it('calls onReset when "Try again" is clicked', async () => {
    const user = userEvent.setup();
    const onReset = vi.fn();
    render(<ErrorMessage error={testError} onReset={onReset} />);
    await user.click(screen.getByRole('button', { name: /try again/i }));
    expect(onReset).toHaveBeenCalledOnce();
  });
});
