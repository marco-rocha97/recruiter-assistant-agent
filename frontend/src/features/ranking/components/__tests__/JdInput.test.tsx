import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { JdInput } from '../JdInput';

describe('JdInput', () => {
  it('renders a textarea and a submit button', () => {
    render(<JdInput onSubmit={() => {}} disabled={false} />);
    expect(screen.getByRole('textbox')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /find candidates/i })).toBeInTheDocument();
  });

  it('submit button is disabled when textarea is empty', () => {
    render(<JdInput onSubmit={() => {}} disabled={false} />);
    expect(screen.getByRole('button', { name: /find candidates/i })).toBeDisabled();
  });

  it('submit button becomes enabled after typing 50+ characters', async () => {
    const user = userEvent.setup();
    render(<JdInput onSubmit={() => {}} disabled={false} />);
    const textarea = screen.getByRole('textbox');
    await user.type(textarea, 'a'.repeat(50));
    expect(screen.getByRole('button', { name: /find candidates/i })).toBeEnabled();
  });

  it('calls onSubmit with the textarea value on form submit', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<JdInput onSubmit={onSubmit} disabled={false} />);
    const textarea = screen.getByRole('textbox');
    const longText = 'a'.repeat(50);
    await user.type(textarea, longText);
    await user.click(screen.getByRole('button', { name: /find candidates/i }));
    expect(onSubmit).toHaveBeenCalledWith(longText);
  });
});
