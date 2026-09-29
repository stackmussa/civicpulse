import { useEffect, useState } from 'react';
import { getStats } from '../api/client';
import type { StatsResponse } from '../api/types';

const CATEGORY_COLORS: Record<string, string> = {
  water: '#3b82f6',
  electricity: '#f59e0b',
  sanitation: '#10b981',
  roads: '#8b5cf6',
  streetlights: '#f97316',
  other: '#6b7280',
};

const PRIORITY_COLORS: Record<string, string> = {
  high: '#ef4444',
  normal: '#3b82f6',
  low: '#10b981',
};

export function StatsPage() {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [cacheHit, setCacheHit] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const { stats: data, cacheHit: hit } = await getStats();
      setStats(data);
      setCacheHit(hit);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const maxCategoryCount = stats
    ? Math.max(...stats.by_category.map((c) => c.count), 1)
    : 1;
  const maxPriorityCount = stats
    ? Math.max(...stats.by_priority.map((p) => p.count), 1)
    : 1;

  return (
    <div className="page stats-page">
      <div className="page-header">
        <h1>Statistics</h1>
        <div className="page-header-actions">
          {cacheHit !== null && (
            <span className={`badge ${cacheHit ? 'badge-cache-hit' : 'badge-cache-miss'}`}>
              X-Cache: {cacheHit ? 'HIT' : 'MISS'}
            </span>
          )}
          <button className="btn btn-sm" onClick={fetchStats} disabled={loading}>
            Refresh
          </button>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {loading && <div className="loading-indicator"><span className="spinner" /> Loading stats…</div>}

      {!loading && stats && (
        <>
          <div className="stats-total">
            <div className="card stat-total-card">
              <span className="stat-number">{stats.total}</span>
              <span className="stat-label">Total Complaints</span>
            </div>
          </div>

          <div className="stats-grid">
            {/* By Category */}
            <div className="card stats-card">
              <h2>By Category</h2>
              <div className="bar-chart">
                {stats.by_category.map((item) => (
                  <div key={item.category} className="bar-row">
                    <span className="bar-label">{item.category}</span>
                    <div className="bar-track">
                      <div
                        className="bar-fill"
                        style={{
                          width: `${(item.count / maxCategoryCount) * 100}%`,
                          backgroundColor: CATEGORY_COLORS[item.category] || '#6b7280',
                        }}
                      />
                    </div>
                    <span className="bar-value">{item.count}</span>
                  </div>
                ))}
                {stats.by_category.length === 0 && (
                  <p className="text-muted">No data</p>
                )}
              </div>
            </div>

            {/* By Priority */}
            <div className="card stats-card">
              <h2>By Priority</h2>
              <div className="bar-chart">
                {stats.by_priority.map((item) => (
                  <div key={item.priority} className="bar-row">
                    <span className="bar-label">{item.priority}</span>
                    <div className="bar-track">
                      <div
                        className="bar-fill"
                        style={{
                          width: `${(item.count / maxPriorityCount) * 100}%`,
                          backgroundColor: PRIORITY_COLORS[item.priority] || '#6b7280',
                        }}
                      />
                    </div>
                    <span className="bar-value">{item.count}</span>
                  </div>
                ))}
                {stats.by_priority.length === 0 && (
                  <p className="text-muted">No data</p>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
