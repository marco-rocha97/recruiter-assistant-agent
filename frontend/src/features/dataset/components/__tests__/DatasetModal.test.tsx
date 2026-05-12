import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi } from 'vitest';
import { DatasetModal } from '../DatasetModal';
import * as api from '../../api';
import type { DatasetInfo } from '../../types';

vi.mock('../../api');

const FIXTURE: DatasetInfo = {
  total_source: 9544,
  total_selected: 50,
  total_included: 49,
  total_excluded: 1,
  exclusions: [
    { source_id: '3054', category: 'Network Support Engineer', reason: 'no_skills' },
  ],
};

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

function renderModal(onClose = vi.fn()) {
  return render(<DatasetModal onClose={onClose} />, { wrapper });
}

describe('DatasetModal', () => {
  it('shows loading text while data is pending', () => {
    vi.mocked(api.useDatasetInfo).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as ReturnType<typeof api.useDatasetInfo>);

    renderModal();
    expect(screen.getByText(/loading dataset info/i)).toBeInTheDocument();
  });

  it('shows dataset stats and exclusion log on success', () => {
    vi.mocked(api.useDatasetInfo).mockReturnValue({
      data: FIXTURE,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof api.useDatasetInfo>);

    renderModal();
    expect(screen.getByText('49')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('3054')).toBeInTheDocument();
    expect(screen.getByText('Network Support Engineer')).toBeInTheDocument();
    expect(screen.getByText('no_skills')).toBeInTheDocument();
  });

  it('shows error message when data is unavailable', () => {
    vi.mocked(api.useDatasetInfo).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as ReturnType<typeof api.useDatasetInfo>);

    renderModal();
    expect(screen.getByText(/temporarily unavailable/i)).toBeInTheDocument();
  });

  it('calls onClose when close button is clicked', async () => {
    const user = userEvent.setup();
    vi.mocked(api.useDatasetInfo).mockReturnValue({
      data: FIXTURE,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof api.useDatasetInfo>);

    const onClose = vi.fn();
    renderModal(onClose);
    await user.click(screen.getByRole('button', { name: /close dataset info/i }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('calls onClose when Escape key is pressed', () => {
    vi.mocked(api.useDatasetInfo).mockReturnValue({
      data: FIXTURE,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof api.useDatasetInfo>);

    const onClose = vi.fn();
    renderModal(onClose);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('calls onClose when backdrop is clicked', async () => {
    const user = userEvent.setup();
    vi.mocked(api.useDatasetInfo).mockReturnValue({
      data: FIXTURE,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof api.useDatasetInfo>);

    const onClose = vi.fn();
    const { container } = renderModal(onClose);
    // The backdrop is the outermost div (fixed overlay)
    const backdrop = container.firstChild as HTMLElement;
    await user.click(backdrop);
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('does not call onClose when the panel (dialog) is clicked', async () => {
    const user = userEvent.setup();
    vi.mocked(api.useDatasetInfo).mockReturnValue({
      data: FIXTURE,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof api.useDatasetInfo>);

    const onClose = vi.fn();
    renderModal(onClose);
    const panel = screen.getByRole('dialog');
    await user.click(panel);
    expect(onClose).not.toHaveBeenCalled();
  });
});
