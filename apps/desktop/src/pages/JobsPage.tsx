/**
 * Jobs / Background Tasks Page
 * 
 * Displays background job status, allows manual triggering,
 * and shows job statistics.
 */

import { useState } from "react";
import { useJobs, useJobStats } from "../lib/hooks";

interface Job {
  job_id: string;
  status: string;
  result?: any;
  error?: string;
  created_at?: string;
  completed_at?: string;
}

export default function JobsPage() {
  const { data: jobsData, isLoading: jobsLoading, refetch } = useJobs(50);
  const { data: statsData } = useJobStats();
  const [manualJobName, setManualJobName] = useState("");
  const [isEnqueuing, setIsEnqueuing] = useState(false);

  const handleEnqueue = async () => {
    if (!manualJobName.trim()) return;
    
    setIsEnqueuing(true);
    try {
      const response = await fetch('http://127.0.0.1:8000/jobs/enqueue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_name: manualJobName,
          kwargs: {},
        }),
      });
      
      if (response.ok) {
        alert(`Job enqueued successfully!`);
        setManualJobName("");
        refetch();
      } else {
        const error = await response.text();
        alert(`Failed to enqueue job: ${error}`);
      }
    } catch (err) {
      alert(`Error: ${err}`);
    } finally {
      setIsEnqueuing(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'var(--success-color)';
      case 'failed': return 'var(--error-color)';
      case 'running': return 'var(--accent-color)';
      case 'queued': return 'var(--warning-color)';
      default: return 'var(--text-muted)';
    }
  };

  return (
    <div style={{ padding: '20px', height: '100%', overflow: 'auto' }}>
      <h1 style={{ marginBottom: '20px' }}>Background Tasks</h1>

      {/* Job Statistics */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '16px',
        marginBottom: '24px',
      }}>
        <div className="card" style={{ background: 'var(--bg-secondary)', padding: '16px' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>Total Jobs</div>
          <div style={{ fontSize: '24px', fontWeight: 700 }}>
            {statsData?.total_jobs || 0}
          </div>
        </div>
        
        <div className="card" style={{ background: 'var(--bg-secondary)', padding: '16px' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>Completed</div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--success-color)' }}>
            {statsData?.status_counts?.completed || 0}
          </div>
        </div>
        
        <div className="card" style={{ background: 'var(--bg-secondary)', padding: '16px' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>Running</div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--accent-color)' }}>
            {statsData?.status_counts?.running || 0}
          </div>
        </div>
        
        <div className="card" style={{ background: 'var(--bg-secondary)', padding: '16px' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>Failed</div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--error-color)' }}>
            {statsData?.status_counts?.failed || 0}
          </div>
        </div>
      </div>

      {/* Manual Job Enqueue */}
      <div className="card" style={{ 
        background: 'var(--bg-secondary)', 
        padding: '16px', 
        marginBottom: '24px',
      }}>
        <h3 style={{ marginTop: 0, marginBottom: '16px' }}>Manually Trigger Job</h3>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end' }}>
          <div style={{ flex: 1 }}>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '13px' }}>Job Name</label>
            <input
              type="text"
              className="input"
              value={manualJobName}
              onChange={(e) => setManualJobName(e.target.value)}
              placeholder="run_daily_briefing, run_hourly_snapshot, etc."
              style={{ width: '100%' }}
            />
          </div>
          <button
            className="btn btn-primary"
            onClick={handleEnqueue}
            disabled={isEnqueuing || !manualJobName.trim()}
          >
            {isEnqueuing ? 'Enqueuing...' : 'Enqueue Job'}
          </button>
        </div>
        <div style={{ marginTop: '12px', fontSize: '12px', color: 'var(--text-muted)' }}>
          Available jobs: run_daily_briefing, run_hourly_snapshot, run_workspace_audit, run_memory_consolidation
        </div>
      </div>

      {/* Job List */}
      <div className="card" style={{ background: 'var(--bg-secondary)', padding: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 style={{ margin: 0 }}>Recent Jobs</h3>
          <button className="btn btn-secondary" onClick={() => refetch()}>
            🔄 Refresh
          </button>
        </div>

        {jobsLoading ? (
          <div className="empty-state">
            <div className="spinner" />
            <div>Loading jobs...</div>
          </div>
        ) : !jobsData?.jobs || jobsData.jobs.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📋</div>
            <div className="empty-state-title">No Jobs Yet</div>
            <div className="empty-state-text">
              Background jobs will appear here once they start running
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {jobsData.jobs.map((job: Job) => (
              <div
                key={job.job_id}
                style={{
                  background: 'var(--bg-input)',
                  padding: '12px',
                  borderRadius: '8px',
                  border: `1px solid ${getStatusColor(job.status)}`,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                      {job.job_id}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      Status: <span style={{ color: getStatusColor(job.status) }}>{job.status}</span>
                      {job.created_at && ` • Created: ${new Date(job.created_at).toLocaleString()}`}
                      {job.completed_at && ` • Completed: ${new Date(job.completed_at).toLocaleString()}`}
                    </div>
                    {job.error && (
                      <div style={{
                        marginTop: '8px',
                        fontSize: '11px',
                        color: 'var(--error-color)',
                        fontFamily: 'monospace',
                        background: 'var(--job-error-bg)',
                        padding: '8px',
                        borderRadius: '4px',
                      }}>
                        Error: {job.error}
                      </div>
                    )}
                    {job.result && (
                      <details style={{ marginTop: '8px' }}>
                        <summary style={{ fontSize: '11px', cursor: 'pointer', color: 'var(--text-muted)' }}>
                          View Result
                        </summary>
                        <pre style={{ 
                          marginTop: '8px', 
                          fontSize: '10px', 
                          fontFamily: 'monospace',
                          background: 'var(--bg-input)',
                          padding: '8px',
                          borderRadius: '4px',
                          overflow: 'auto',
                          maxHeight: '200px',
                        }}>
                          {JSON.stringify(job.result, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
