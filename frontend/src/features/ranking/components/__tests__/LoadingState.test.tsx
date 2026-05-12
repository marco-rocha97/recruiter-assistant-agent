import { render, screen } from '@testing-library/react';
import { LoadingState } from '../LoadingState';

describe('LoadingState', () => {
  it('renders the analyzing message', () => {
    render(<LoadingState />);
    expect(screen.getByText(/analyzing candidates/i)).toBeInTheDocument();
  });

  it('has a status role for screen-reader announcements', () => {
    render(<LoadingState />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });
});
