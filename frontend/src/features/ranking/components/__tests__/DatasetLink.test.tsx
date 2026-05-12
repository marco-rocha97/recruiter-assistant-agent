import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import { DatasetLink } from '../../../../components/DatasetLink';

describe('DatasetLink', () => {
  it('renders a button labelled "About this dataset"', () => {
    render(<DatasetLink onOpen={() => {}} />);
    expect(screen.getByRole('button', { name: /about this dataset/i })).toBeInTheDocument();
  });

  it('calls onOpen when clicked', async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    render(<DatasetLink onOpen={onOpen} />);
    await user.click(screen.getByRole('button', { name: /about this dataset/i }));
    expect(onOpen).toHaveBeenCalledOnce();
  });
});
