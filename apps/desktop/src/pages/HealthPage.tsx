/**
 * System Health Dashboard - Enhanced with System Monitor
 *
 * Displays:
 * - FastAPI Backend status
 * - Qdrant (Vector DB) status
 * - Redis (Job Queue) status
 * - ARQ Worker status
 * - CPU usage (NEW)
 * - Memory usage (NEW)
 * - Disk usage (NEW)
 * - Battery status (NEW - laptops only)
 */

import { useState, useEffect } from "react";
import {
  getSystemSummary,
  type SystemSummary,
} from "../lib/api";

interface ServiceStatus {
  name: string;
  status: 'healthy' | 'degraded' | 'offline';
  port?: number;
  details?: string;
}

export default function HealthPage() {
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [systemMetrics, setSystemMetrics] = useState<SystemSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [metricsLoading, setMetricsLoading] = useState(false);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  // Separate interval for system metrics (more frequent)
  useEffect(() => {
    loadSystemMetrics();
    const interval = setInterval(loadSystemMetrics, 10000); // Refresh every 10 seconds
    return () => clearInterval(interval);
  }, []);

  const checkHealth = async () => {
    setLoading(true);
    try {
      const [healthRes, memoryHealthRes, jobsStatsRes, redisHealthRes] = await Promise.all([
        fetch('http://127.0.0.1:8000/health'),
        fetch('http://127.0.0.1:8000/memory/health'),
        fetch('http://127.0.0.1:8000/jobs/stats'),
        fetch('http://127.0.0.1:8000/jobs/health'),
      ]);

      const health = await healthRes.json();
      const memoryHealth = await memoryHealthRes.json();
      const jobsStats = await jobsStatsRes.json();
      const redisHealthData = await redisHealthRes.json();

      const serviceList: ServiceStatus[] = [
        {
          name: 'FastAPI Backend',
          status: health.status === 'ok' ? 'healthy' : 'degraded',
          port: 8000,
          details: `Version: ${health.version || '0.2.0'}`,
        },
        {
          name: 'Qdrant (Vector DB)',
          status: memoryHealth.qdrant === 'connected' ? 'healthy' : 'offline',
          port: 6333,
          details: memoryHealth.collections ?
            `Collections: ${memoryHealth.collections.length}` :
            memoryHealth.error,
        },
        {
          name: 'Redis (Job Queue)',
          status: redisHealthData.connected ? 'healthy' : 'offline',
          port: 6379,
          details: redisHealthData.connected ?
            `Keys: ${redisHealthData.keys_count}, Memory: ${redisHealthData.memory_used || 'N/A'}` :
            redisHealthData.error,
        },
        {
          name: 'ARQ Worker',
          status: jobsStats.redis_connected && jobsStats.total_jobs !== undefined ? 'healthy' : 'offline',
          details: jobsStats.redis_connected ?
            `Total: ${jobsStats.total_jobs}, Running: ${jobsStats.status_counts?.running || 0}` :
            'Not running (start with: arq packages.automation.arq_worker.WorkerSettings)',
        },
      ];

      setServices(serviceList);

    } catch (err) {
      console.error('Health check failed:', err);
      setServices([
        { name: 'FastAPI Backend', status: 'offline', port: 8000, details: 'Cannot connect' },
        { name: 'Qdrant (Vector DB)', status: 'offline', port: 6333 },
        { name: 'Redis (Job Queue)', status: 'offline', port: 6379 },
        { name: 'ARQ Worker', status: 'offline', details: 'Health check failed' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const loadSystemMetrics = async () => {
    setMetricsLoading(true);
    try {
      const summary = await getSystemSummary();
      setSystemMetrics(summary);
    } catch (err) {
      console.error('Failed to load system metrics:', err);
    } finally {
      setMetricsLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'var(--success-color)';
      case 'degraded': return 'var(--warning-color)';
      case 'offline': return 'var(--error-color)';
      default: return 'var(--text-muted)';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy': return '✅';
      case 'degraded': return '⚠️';
      case 'offline': return '❌';
      default: return '❓';
    }
  };

  const healthyCount = services.filter(s => s.status === 'healthy').length;
  const totalServices = services.length;

  const formatBytes = (gb: number | undefined) => {
    if (gb === undefined || gb === null) return 'N/A';
    if (gb >= 1000) {
      return `${(gb / 1000).toFixed(1)} TB`;
    }
    return `${gb.toFixed(1)} GB`;
  };

  const getUsageColor = (percent: number) => {
    if (percent >= 90) return 'var(--error-color)';
    if (percent >= 70) return 'var(--warning-color)';
    return 'var(--success-color)';
  };

  return (
    <div style={{ padding: '20px', height: '100%', overflow: 'auto' }}>
      <h1 style={{ marginBottom: '20px' }}>System Health Dashboard</h1>

      {/* Overall Status */}
      <div style={{
        marginBottom: '24px',
        padding: '16px',
        background: healthyCount === totalServices ? 'var(--success-bg)' :
                     healthyCount > 0 ? 'var(--warning-bg)' : 'var(--error-bg)',
        borderRadius: '8px',
        border: `1px solid ${healthyCount === totalServices ? 'var(--success-color)' :
                           healthyCount > 0 ? 'var(--warning-color)' : 'var(--error-color)'}`,
      }}>
        <div style={{ fontSize: '14px', fontWeight: 600, marginBottom: '4px' }}>
          {healthyCount === totalServices ? '✅ All Systems Operational' :
           healthyCount > 0 ? '⚠️ Some Services Degraded' : '❌ Services Offline'}
        </div>
        <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
          {healthyCount}/{totalServices} services healthy
        </div>
      </div>

      {/* Service Status */}
      <section className="card" style={{
        background: 'var(--bg-secondary)',
        padding: '20px',
        marginBottom: '24px',
      }}>
        <h2 style={{ marginTop: 0, marginBottom: '16px' }}>🖥️ Service Status</h2>

        {loading ? (
          <div className="empty-state">
            <div className="empty-state-text">Loading service status...</div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {services.map((service) => (
              <div
                key={service.name}
                style={{
                  background: 'var(--bg-input)',
                  padding: '16px',
                  borderRadius: '8px',
                  border: `1px solid ${getStatusColor(service.status)}`,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '16px',
                }}
              >
                <div style={{ fontSize: '24px' }}>
                  {getStatusIcon(service.status)}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '14px', fontWeight: 600, marginBottom: '4px' }}>
                    {service.name}
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    {service.details || 'No details'}
                    {service.port && ` • Port: ${service.port}`}
                  </div>
                </div>
                <div style={{
                  padding: '4px 12px',
                  borderRadius: '12px',
                  background: getStatusColor(service.status),
                  color: 'white',
                  fontSize: '11px',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                }}>
                  {service.status}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* System Metrics */}
      <section className="card" style={{
        background: 'var(--bg-secondary)',
        padding: '20px',
        marginBottom: '24px',
      }}>
        <h2 style={{ marginTop: 0, marginBottom: '16px' }}>📊 System Metrics</h2>

        {metricsLoading && !systemMetrics ? (
          <div className="empty-state">
            <div className="empty-state-text">Loading system metrics...</div>
          </div>
        ) : systemMetrics ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
            
            {/* CPU Card */}
            {systemMetrics.cpu.available ? (
              <div style={{
                background: 'var(--bg-input)',
                padding: '16px',
                borderRadius: '8px',
                border: '1px solid var(--border)',
              }}>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                  ⚡ CPU Usage
                </div>
                <div style={{ fontSize: '28px', fontWeight: 700, marginBottom: '8px', color: getUsageColor(systemMetrics.cpu.usage_percent) }}>
                  {systemMetrics.cpu.usage_percent.toFixed(1)}%
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  <div>{systemMetrics.cpu.cores_physical}P + {systemMetrics.cpu.cores_logical}E cores</div>
                  <div>{(systemMetrics.cpu.frequency_mhz / 1000).toFixed(2)} GHz</div>
                </div>
                <div style={{
                  marginTop: '12px',
                  height: '6px',
                  background: 'var(--border)',
                  borderRadius: '3px',
                  overflow: 'hidden',
                }}>
                  <div style={{
                    width: `${systemMetrics.cpu.usage_percent}%`,
                    height: '100%',
                    background: getUsageColor(systemMetrics.cpu.usage_percent),
                    transition: 'width 0.3s ease',
                  }} />
                </div>
              </div>
            ) : (
              <div style={{
                background: 'var(--bg-input)',
                padding: '16px',
                borderRadius: '8px',
                border: '1px solid var(--border)',
                opacity: 0.6,
              }}>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                  ⚡ CPU Usage
                </div>
                <div style={{ fontSize: '14px', color: 'var(--error-color)' }}>
                  {systemMetrics.cpu.error || 'Not available'}
                </div>
              </div>
            )}

            {/* Memory Card */}
            {systemMetrics.memory.available ? (
              <div style={{
                background: 'var(--bg-input)',
                padding: '16px',
                borderRadius: '8px',
                border: '1px solid var(--border)',
              }}>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                  🧠 Memory
                </div>
                <div style={{ fontSize: '28px', fontWeight: 700, marginBottom: '8px', color: getUsageColor(systemMetrics.memory.usage_percent) }}>
                  {systemMetrics.memory.usage_percent.toFixed(1)}%
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  <div>{formatBytes(systemMetrics.memory.used_gb)} / {formatBytes(systemMetrics.memory.total_gb)} used</div>
                  <div>{formatBytes(systemMetrics.memory.available_gb)} available</div>
                </div>
                <div style={{
                  marginTop: '12px',
                  height: '6px',
                  background: 'var(--border)',
                  borderRadius: '3px',
                  overflow: 'hidden',
                }}>
                  <div style={{
                    width: `${systemMetrics.memory.usage_percent}%`,
                    height: '100%',
                    background: getUsageColor(systemMetrics.memory.usage_percent),
                    transition: 'width 0.3s ease',
                  }} />
                </div>
              </div>
            ) : (
              <div style={{
                background: 'var(--bg-input)',
                padding: '16px',
                borderRadius: '8px',
                border: '1px solid var(--border)',
                opacity: 0.6,
              }}>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                  🧠 Memory
                </div>
                <div style={{ fontSize: '14px', color: 'var(--error-color)' }}>
                  {systemMetrics.memory.error || 'Not available'}
                </div>
              </div>
            )}

            {/* Disk Card */}
            {systemMetrics.disk && systemMetrics.disk.length > 0 && systemMetrics.disk[0].total_gb ? (
              <div style={{
                background: 'var(--bg-input)',
                padding: '16px',
                borderRadius: '8px',
                border: '1px solid var(--border)',
              }}>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                  💾 Disk Usage
                </div>
                {systemMetrics.disk.filter(d => d.total_gb).slice(0, 2).map((drive, idx) => (
                  <div key={idx} style={{ marginBottom: idx < systemMetrics.disk.length - 1 ? '12px' : '0' }}>
                    <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                      {drive.device} ({drive.fstype})
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                      {formatBytes(drive.used_gb)} / {formatBytes(drive.total_gb)} used
                    </div>
                    <div style={{
                      height: '4px',
                      background: 'var(--border)',
                      borderRadius: '2px',
                      overflow: 'hidden',
                    }}>
                      <div style={{
                        width: `${drive.usage_percent}%`,
                        height: '100%',
                        background: getUsageColor(drive.usage_percent),
                        transition: 'width 0.3s ease',
                      }} />
                    </div>
                  </div>
                ))}
                {systemMetrics.disk.length > 2 && (
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '8px' }}>
                    +{systemMetrics.disk.length - 2} more drives
                  </div>
                )}
              </div>
            ) : (
              <div style={{
                background: 'var(--bg-input)',
                padding: '16px',
                borderRadius: '8px',
                border: '1px solid var(--border)',
                opacity: 0.6,
              }}>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                  💾 Disk Usage
                </div>
                <div style={{ fontSize: '14px', color: 'var(--error-color)' }}>
                  {systemMetrics.disk?.[0]?.error || 'Not available'}
                </div>
              </div>
            )}

            {/* Battery Card */}
            {systemMetrics.battery.present && systemMetrics.battery.available ? (
              <div style={{
                background: 'var(--bg-input)',
                padding: '16px',
                borderRadius: '8px',
                border: '1px solid var(--border)',
              }}>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                  🔋 Battery
                </div>
                <div style={{ fontSize: '28px', fontWeight: 700, marginBottom: '8px' }}>
                  {systemMetrics.battery.percent}%
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  <div>Status: {systemMetrics.battery.status}</div>
                  {systemMetrics.battery.power_plugged && (
                    <div style={{ color: 'var(--success-color)' }}>🔌 Plugged in</div>
                  )}
                  {!systemMetrics.battery.power_plugged && systemMetrics.battery.time_left_minutes && systemMetrics.battery.time_left_minutes > 0 && (
                    <div>~{Math.floor(systemMetrics.battery.time_left_minutes / 60)}h {systemMetrics.battery.time_left_minutes % 60}m remaining</div>
                  )}
                </div>
                <div style={{
                  marginTop: '12px',
                  height: '6px',
                  background: 'var(--border)',
                  borderRadius: '3px',
                  overflow: 'hidden',
                }}>
                  <div style={{
                    width: `${systemMetrics.battery.percent || 0}%`,
                    height: '100%',
                    background: getUsageColor(systemMetrics.battery.percent || 0),
                    transition: 'width 0.3s ease',
                  }} />
                </div>
              </div>
            ) : systemMetrics.battery.present ? (
              <div style={{
                background: 'var(--bg-input)',
                padding: '16px',
                borderRadius: '8px',
                border: '1px solid var(--border)',
                opacity: 0.6,
              }}>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                  🔋 Battery
                </div>
                <div style={{ fontSize: '14px', color: 'var(--error-color)' }}>
                  {systemMetrics.battery.error || 'Not available'}
                </div>
              </div>
            ) : null}
          </div>
        ) : null}

        {/* Refresh indicator */}
        <div style={{
          marginTop: '16px',
          fontSize: '11px',
          color: 'var(--text-muted)',
          textAlign: 'right',
        }}>
          {metricsLoading ? '🔄 Refreshing...' : `Last updated: ${systemMetrics?.timestamp ? new Date(systemMetrics.timestamp).toLocaleTimeString() : 'N/A'}`}
        </div>
      </section>
    </div>
  );
}
