import { useEffect, useState } from 'react';
import { listComplaints, updateStatus } from '../api/client';
import type { Complaint, Category, Priority, Status, PaginatedComplaints } from '../api/types';

const CATEGORIES: Category[] = ['water', 'electricity', 'sanitation', 'roads', 'streetlights', 'other'];
const PRIORITIES: Priority[] = ['high', 'normal', 'low'];
const STATUSES: Status[] = ['open', 'in_progress', 'resolved', 'rejected'];

// Valid transitions matching the backend state machine
const VALID_TRANSITIONS: Record<Status, Status[]> = {
  open: ['in_progress', 'rejected'],
  in_progress: ['resolved', 'rejected'],
  resolved: [],
  rejected: [],
};

export function DashboardPage() {
  const [data, setData] = useState<PaginatedComplaints | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);

  // Filters
  const [filterCategory, setFilterCategory] = useState<Category | ''>('');
  const [filterPriority, setFilterPriority] = useState<Priority | ''>('');
  const [filterStatus, setFilterStatus] = useState<Status | ''>('');
  const [page, setPage] = useState(1);
  const pageSize = 10;

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listComplaints({
        category: filterCategory || undefined,
        priority: filterPriority || undefined,
        status: filterStatus || undefined,
        page,
        page_size: pageSize,
      });
      setData(result);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [filterCategory, filterPriority, filterStatus, page]);

  const handleStatusChange = async (complaint: Complaint, newStatus: Status) => {
    setStatusError(null);
    try {
      await updateStatus(complaint.id, { status: newStatus });
      await fetchData();
    } catch (err: any) {
      if (err.status === 409 && err.body) {
        // Surface the server's 409 message verbatim
        setStatusError(
          `Invalid transition: cannot move from "${err.body.from}" to "${err.body.to}"`
        );
      } else {
        setStatusError(err.message || 'Failed to update status');
      }
    }
  };

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;

  const priorityClass = (p: string) => {
    if (p === 'high') return 'badge badge-high';
    if (p === 'low') return 'badge badge-low';
    return 'badge badge-normal';
  };

  const statusClass = (s: string) => {
    if (s === 'open') return 'badge badge-open';
    if (s === 'in_progress') return 'badge badge-in-progress';
    if (s === 'resolved') return 'badge badge-resolved';
    return 'badge badge-rejected';
  };

  return (
    <div className="page dashboard-page">
      <div className="page-header">
        <h1>Operations Dashboard</h1>
        <p className="page-subtitle">
          {data ? `${data.total} complaints total` : 'Loading…'}
        </p>
      </div>

      {/* Filters */}
      <div className="card filter-bar">
        <div className="filter-group">
          <label>Category</label>
          <select
            value={filterCategory}
            onChange={(e) => { setFilterCategory(e.target.value as Category | ''); setPage(1); }}
          >
            <option value="">All</option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <div className="filter-group">
          <label>Priority</label>
          <select
            value={filterPriority}
            onChange={(e) => { setFilterPriority(e.target.value as Priority | ''); setPage(1); }}
          >
            <option value="">All</option>
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </div>
        <div className="filter-group">
          <label>Status</label>
          <select
            value={filterStatus}
            onChange={(e) => { setFilterStatus(e.target.value as Status | ''); setPage(1); }}
          >
            <option value="">All</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>{s.replace('_', ' ')}</option>
            ))}
          </select>
        </div>
      </div>

      {statusError && (
        <div className="alert alert-error">{statusError}</div>
      )}

      {error && <div className="alert alert-error">{error}</div>}

      {loading && <div className="loading-indicator"><span className="spinner" /> Loading complaints…</div>}

      {!loading && data && (
        <>
          <div className="complaints-table-wrapper">
            <table className="complaints-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Summary</th>
                  <th>Location</th>
                  <th>Category</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th>Provider</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((c) => (
                  <tr key={c.id}>
                    <td className="td-id" title={c.id}>{c.id.slice(0, 8)}…</td>
                    <td className="td-summary">{c.ai_summary || c.text.slice(0, 60) + '…'}</td>
                    <td>{c.location}</td>
                    <td><span className={`badge badge-category-${c.category}`}>{c.category}</span></td>
                    <td><span className={priorityClass(c.priority)}>{c.priority}</span></td>
                    <td><span className={statusClass(c.status)}>{c.status.replace('_', ' ')}</span></td>
                    <td><span className="badge badge-provider">{c.triaged_by}</span></td>
                    <td className="td-actions">
                      {VALID_TRANSITIONS[c.status].length > 0 ? (
                        VALID_TRANSITIONS[c.status].map((s) => (
                          <button
                            key={s}
                            className={`btn btn-sm btn-${s === 'rejected' ? 'danger' : 'primary'}`}
                            onClick={() => handleStatusChange(c, s)}
                          >
                            {s.replace('_', ' ')}
                          </button>
                        ))
                      ) : (
                        <span className="text-muted">terminal</span>
                      )}
                    </td>
                  </tr>
                ))}
                {data.items.length === 0 && (
                  <tr>
                    <td colSpan={8} className="text-center text-muted">No complaints found</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="pagination">
              <button
                className="btn btn-sm"
                disabled={page === 1}
                onClick={() => setPage(page - 1)}
              >
                ← Prev
              </button>
              <span className="pagination-info">
                Page {page} of {totalPages}
              </span>
              <button
                className="btn btn-sm"
                disabled={page === totalPages}
                onClick={() => setPage(page + 1)}
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
