/**
 * Telegram Integration Page - Enhanced with Bot Manager
 *
 * Features:
 * - Bot token configuration with persistence
 * - DM policy settings
 * - Real-time bot status monitoring
 * - Bot lifecycle control (start/stop/reload)
 * - Pending approvals (pairing mode)
 * - Connected users list
 * - Test message capability
 */

import { useState, useEffect, useCallback } from "react";
import {
  getTelegramConfig,
  updateTelegramConfig,
  getTelegramStatus,
  startTelegramBot,
  stopTelegramBot,
  reloadTelegramBot,
  listPendingTelegramUsers,
  listTelegramUsers,
  approveTelegramUser,
  sendTelegramTestMessage,
  type TelegramConfigResponse,
  type TelegramStatus,
  type TelegramUser,
} from "../lib/api";

export default function TelegramPage() {
  // Configuration state
  const [config, setConfig] = useState<TelegramConfigResponse | null>(null);
  const [botToken, setBotToken] = useState("");
  const [dmPolicy, setDmPolicy] = useState<'pairing' | 'allowlist' | 'open'>('pairing');
  
  // Bot status state
  const [botStatus, setBotStatus] = useState<TelegramStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);
  
  // User management state
  const [pendingUsers, setPendingUsers] = useState<TelegramUser[]>([]);
  const [connectedUsers, setConnectedUsers] = useState<TelegramUser[]>([]);
  
  // Action state
  const [saving, setSaving] = useState(false);
  const [actionMessage, setActionMessage] = useState<{type: 'success' | 'error' | 'info', text: string} | null>(null);
  const [testMessageStatus, setTestMessageStatus] = useState<string | null>(null);

  // Load initial data
  useEffect(() => {
    loadConfig();
    loadStatus();
    loadPendingUsers();
    loadConnectedUsers();
  }, []);

  // Poll status when bot is running or reloading
  useEffect(() => {
    if (!botStatus) return;
    
    if (botStatus.state === 'running' || botStatus.state === 'reloading' || botStatus.state === 'starting') {
      const interval = setInterval(() => {
        loadStatus();
      }, 3000); // Poll every 3 seconds
      return () => clearInterval(interval);
    }
  }, [botStatus?.state]);

  const loadConfig = async () => {
    try {
      const data = await getTelegramConfig();
      setConfig(data);
      setDmPolicy(data.dm_policy || 'pairing');
    } catch (err) {
      console.error('Failed to load Telegram config:', err);
      setActionMessage({type: 'error', text: 'Failed to load configuration'});
    }
  };

  const loadStatus = useCallback(async () => {
    setStatusLoading(true);
    try {
      const status = await getTelegramStatus();
      setBotStatus(status);
      
      // Clear action message if bot is now running
      if (status.state === 'running' && actionMessage?.text.includes('starting')) {
        setActionMessage({type: 'success', text: 'Bot started successfully!'});
      }
    } catch (err) {
      console.error('Failed to load Telegram status:', err);
    } finally {
      setStatusLoading(false);
    }
  }, [actionMessage]);

  const loadPendingUsers = async () => {
    try {
      const data = await listPendingTelegramUsers();
      setPendingUsers(data.pending_users || []);
    } catch (err) {
      console.error('Failed to load pending users:', err);
    }
  };

  const loadConnectedUsers = async () => {
    try {
      const data = await listTelegramUsers();
      setConnectedUsers(data.users?.filter((u) => u.approved) || []);
    } catch (err) {
      console.error('Failed to load connected users:', err);
    }
  };

  const handleSaveConfig = async () => {
    setSaving(true);
    setActionMessage(null);
    
    try {
      const result = await updateTelegramConfig({
        bot_token: botToken || undefined,
        dm_policy: dmPolicy,
      });
      
      setActionMessage({type: 'success', text: result.message});
      
      // Reload config and status
      await loadConfig();
      if (result.status === 'reloading') {
        // Status will be polled automatically
      } else {
        await loadStatus();
      }
    } catch (err) {
      setActionMessage({
        type: 'error', 
        text: err instanceof Error ? err.message : 'Failed to save configuration'
      });
    } finally {
      setSaving(false);
    }
  };

  const handleStartBot = async () => {
    setSaving(true);
    setActionMessage(null);
    
    try {
      const result = await startTelegramBot({
        bot_token: botToken || config?.token_display.replace('...', '') || '',
        dm_policy: dmPolicy,
      });
      
      setActionMessage({type: 'info', text: result.message});
      
      // Poll status
      setTimeout(loadStatus, 2000);
    } catch (err) {
      setActionMessage({
        type: 'error', 
        text: err instanceof Error ? err.message : 'Failed to start bot'
      });
    } finally {
      setSaving(false);
    }
  };

  const handleStopBot = async () => {
    setSaving(true);
    setActionMessage(null);
    
    try {
      const result = await stopTelegramBot();
      setActionMessage({type: 'success', text: result.message});
      await loadStatus();
    } catch (err) {
      setActionMessage({
        type: 'error', 
        text: err instanceof Error ? err.message : 'Failed to stop bot'
      });
    } finally {
      setSaving(false);
    }
  };

  const handleReloadBot = async () => {
    if (!botToken && !config?.bot_token_set) {
      setActionMessage({type: 'error', text: 'Bot token required for reload'});
      return;
    }
    
    setSaving(true);
    setActionMessage(null);
    
    try {
      const result = await reloadTelegramBot({
        bot_token: botToken || '',
        dm_policy: dmPolicy,
      });
      
      setActionMessage({type: 'info', text: result.message});
      
      // Poll status
      setTimeout(loadStatus, 2000);
    } catch (err) {
      setActionMessage({
        type: 'error', 
        text: err instanceof Error ? err.message : 'Failed to reload bot'
      });
    } finally {
      setSaving(false);
    }
  };

  const handleApproveUser = async (telegramId: string) => {
    try {
      await approveTelegramUser(telegramId);
      loadPendingUsers();
      loadConnectedUsers();
      setActionMessage({type: 'success', text: 'User approved successfully!'});
    } catch (err) {
      setActionMessage({
        type: 'error', 
        text: err instanceof Error ? err.message : 'Failed to approve user'
      });
    }
  };

  const handleTestMessage = async () => {
    setTestMessageStatus('Sending...');
    try {
      const result = await sendTelegramTestMessage();
      setTestMessageStatus(result.message);
      setActionMessage({type: 'success', text: result.message});
    } catch (err) {
      setTestMessageStatus(`Error: ${err instanceof Error ? err.message : 'Failed to send test message'}`);
      setActionMessage({type: 'error', text: 'Failed to send test message'});
    }
  };

  const getStatusColor = (state: string) => {
    switch (state) {
      case 'running': return 'var(--success-color)';
      case 'starting':
      case 'reloading': return 'var(--warning-color)';
      case 'stopping': return 'var(--text-muted)';
      case 'error': return 'var(--error-color)';
      case 'stopped': return 'var(--text-muted)';
      default: return 'var(--text-muted)';
    }
  };

  const getStatusIcon = (state: string) => {
    switch (state) {
      case 'running': return '🟢';
      case 'starting': return '🟡';
      case 'reloading': return '🔄';
      case 'stopping': return '⏹️';
      case 'error': return '🔴';
      case 'stopped': return '⚫';
      default: return '⚪';
    }
  };

  const formatUptime = (seconds?: number) => {
    if (!seconds) return 'N/A';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    if (hours > 0) {
      return `${hours}h ${minutes}m ${secs}s`;
    }
    if (minutes > 0) {
      return `${minutes}m ${secs}s`;
    }
    return `${secs}s`;
  };

  return (
    <div style={{ padding: '20px', height: '100%', overflow: 'auto' }}>
      <h1 style={{ marginBottom: '24px' }}>Telegram Integration</h1>

      {/* Action Message */}
      {actionMessage && (
        <div style={{
          marginBottom: '20px',
          padding: '12px',
          borderRadius: '8px',
          background: actionMessage.type === 'success' ? 'var(--success-bg)' :
                       actionMessage.type === 'error' ? 'var(--error-bg)' : 'var(--info-bg)',
          border: `1px solid ${actionMessage.type === 'success' ? 'var(--success-color)' :
                                 actionMessage.type === 'error' ? 'var(--error-color)' : 'var(--info-color)'}`,
          fontSize: '13px',
          color: actionMessage.type === 'success' ? 'var(--success-color)' :
                 actionMessage.type === 'error' ? 'var(--error-color)' : 'var(--info-color)',
        }}>
          {actionMessage.text}
        </div>
      )}

      {/* Bot Status Card */}
      <section className="card" style={{
        background: 'var(--bg-secondary)',
        padding: '20px',
        marginBottom: '24px',
      }}>
        <h2 style={{ marginTop: 0, marginBottom: '16px' }}>🤖 Bot Status</h2>
        
        {botStatus ? (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
            padding: '16px',
            background: 'var(--bg-input)',
            borderRadius: '8px',
            border: '1px solid var(--border)',
          }}>
            <div style={{ fontSize: '32px' }}>
              {getStatusIcon(botStatus.state)}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '14px', fontWeight: 600, marginBottom: '4px' }}>
                State: <span style={{ color: getStatusColor(botStatus.state) }}>{botStatus.state.toUpperCase()}</span>
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                DM Policy: {botStatus.dm_policy}
              </div>
              {botStatus.started_at && (
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Uptime: {formatUptime(botStatus.uptime_seconds)}
                </div>
              )}
              {botStatus.error_message && (
                <div style={{ fontSize: '12px', color: 'var(--error-color)', marginTop: '4px' }}>
                  Error: {botStatus.error_message}
                </div>
              )}
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              {botStatus.state === 'running' ? (
                <>
                  <button
                    className="btn btn-secondary"
                    onClick={handleStopBot}
                    disabled={saving}
                  >
                    ⏹️ Stop
                  </button>
                  <button
                    className="btn btn-secondary"
                    onClick={handleReloadBot}
                    disabled={saving}
                  >
                    🔄 Reload
                  </button>
                </>
              ) : botStatus.state === 'stopped' ? (
                <button
                  className="btn btn-primary"
                  onClick={handleStartBot}
                  disabled={saving || !config?.bot_token_set}
                >
                  ▶️ Start
                </button>
              ) : (
                <div style={{
                  padding: '8px 16px',
                  fontSize: '13px',
                  color: 'var(--text-muted)',
                }}>
                  {botStatus.state === 'starting' && '⏳ Starting...'}
                  {botStatus.state === 'stopping' && '⏹️ Stopping...'}
                  {botStatus.state === 'reloading' && '🔄 Reloading...'}
                </div>
              )}
            </div>
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
            {statusLoading ? 'Loading status...' : 'Failed to load bot status'}
          </div>
        )}
      </section>

      {/* Bot Configuration */}
      <section className="card" style={{
        background: 'var(--bg-secondary)',
        padding: '20px',
        marginBottom: '24px',
      }}>
        <h2 style={{ marginTop: 0, marginBottom: '16px' }}>⚙️ Bot Configuration</h2>

        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontSize: '13px' }}>
            Bot Token (from @BotFather)
          </label>
          <input
            type="password"
            className="input"
            value={botToken}
            onChange={(e) => setBotToken(e.target.value)}
            placeholder="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
            style={{ width: '100%', fontFamily: 'monospace' }}
          />
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Current: {config?.bot_token_set ? `✅ Configured (${config.token_display})` : '❌ Not configured'}
          </div>
        </div>

        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontSize: '13px' }}>
            DM Policy
          </label>
          <select
            className="input"
            value={dmPolicy}
            onChange={(e) => setDmPolicy(e.target.value as any)}
            style={{ width: '100%' }}
          >
            <option value="pairing">Pairing (require approval code)</option>
            <option value="allowlist">Allowlist only</option>
            <option value="open">Open (anyone can message)</option>
          </select>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
            {dmPolicy === 'pairing' && 'Users need approval code from administrator'}
            {dmPolicy === 'allowlist' && 'Only pre-approved users can message'}
            {dmPolicy === 'open' && 'Anyone can message the bot'}
          </div>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            className="btn btn-primary"
            onClick={handleSaveConfig}
            disabled={saving}
          >
            {saving ? 'Saving...' : '💾 Save Configuration'}
          </button>
          {botStatus?.state === 'running' && (
            <button
              className="btn btn-secondary"
              onClick={handleReloadBot}
              disabled={saving || !botToken}
            >
              🔄 Save & Reload
            </button>
          )}
        </div>
      </section>

      {/* Test Message */}
      <section className="card" style={{
        background: 'var(--bg-secondary)',
        padding: '20px',
        marginBottom: '24px',
      }}>
        <h2 style={{ marginTop: 0, marginBottom: '16px' }}>🧪 Test Connection</h2>

        <button
          className="btn btn-secondary"
          onClick={handleTestMessage}
          disabled={!botStatus || botStatus.state !== 'running'}
        >
          Send Test Message
        </button>

        {testMessageStatus && (
          <div style={{
            marginTop: '12px',
            padding: '12px',
            borderRadius: '8px',
            background: testMessageStatus.includes('Error') ? 'var(--error-bg)' : 'var(--success-bg)',
            border: `1px solid ${testMessageStatus.includes('Error') ? 'var(--error-color)' : 'var(--success-color)'}`,
            fontSize: '13px',
            color: testMessageStatus.includes('Error') ? 'var(--error-color)' : 'var(--success-color)',
          }}>
            {testMessageStatus}
          </div>
        )}
      </section>

      {/* Pending Approvals */}
      {dmPolicy === 'pairing' && (
        <section className="card" style={{
          background: 'var(--bg-secondary)',
          padding: '20px',
          marginBottom: '24px',
        }}>
          <h2 style={{ marginTop: 0, marginBottom: '16px' }}>⏳ Pending Approvals</h2>

          {pendingUsers.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">✅</div>
              <div className="empty-state-title">No Pending Approvals</div>
              <div className="empty-state-text">
                All users have been approved
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {pendingUsers.map((user) => (
                <div
                  key={user.telegram_id}
                  style={{
                    background: 'var(--bg-input)',
                    padding: '12px',
                    borderRadius: '8px',
                    border: '1px solid var(--border)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: 600 }}>
                      Telegram ID: {user.telegram_id}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      User ID: {user.user_id} • Created: {new Date(user.created_at).toLocaleString()}
                    </div>
                  </div>
                  <button
                    className="btn btn-success"
                    onClick={() => handleApproveUser(user.telegram_id)}
                  >
                    ✅ Approve
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* Connected Users */}
      <section className="card" style={{
        background: 'var(--bg-secondary)',
        padding: '20px',
        marginBottom: '24px',
      }}>
        <h2 style={{ marginTop: 0, marginBottom: '16px' }}>👥 Connected Users</h2>

        {connectedUsers.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">👥</div>
            <div className="empty-state-title">No Connected Users</div>
            <div className="empty-state-text">
              Users will appear here once they connect to the bot
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {connectedUsers.map((user) => (
              <div
                key={user.telegram_id}
                style={{
                  background: 'var(--bg-input)',
                  padding: '12px',
                  borderRadius: '8px',
                  border: '1px solid var(--border)',
                }}
              >
                <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                  Telegram ID: {user.telegram_id}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  User ID: {user.user_id} • Created: {new Date(user.created_at).toLocaleString()}
                  {user.last_message_at && (
                    <> • Last Active: {new Date(user.last_message_at).toLocaleString()}</>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Setup Instructions */}
      <section className="card" style={{
        background: 'var(--bg-secondary)',
        padding: '20px',
      }}>
        <h2 style={{ marginTop: 0, marginBottom: '16px' }}>📚 Setup Instructions</h2>

        <div style={{ fontSize: '13px', lineHeight: 1.8 }}>
          <h3 style={{ fontSize: '14px', marginBottom: '8px' }}>1. Create a Bot</h3>
          <ol style={{ paddingLeft: '20px', marginBottom: '16px' }}>
            <li>Open Telegram and search for <strong>@BotFather</strong></li>
            <li>Send <code>/newbot</code> and follow the instructions</li>
            <li>Choose a name and username for your bot</li>
            <li>Copy the bot token provided by BotFather</li>
          </ol>

          <h3 style={{ fontSize: '14px', marginBottom: '8px' }}>2. Configure the Bot</h3>
          <ol style={{ paddingLeft: '20px', marginBottom: '16px' }}>
            <li>Paste the bot token in the "Bot Token" field above</li>
            <li>Choose your preferred DM Policy</li>
            <li>Click "Save Configuration"</li>
            <li>Click "Start" to start the bot</li>
          </ol>

          <h3 style={{ fontSize: '14px', marginBottom: '8px' }}>3. Test the Connection</h3>
          <ol style={{ paddingLeft: '20px' }}>
            <li>Click "Send Test Message" to verify the bot is working</li>
            <li>Users can now message your bot on Telegram</li>
            {dmPolicy === 'pairing' && (
              <>
                <li>Approve pending users from the "Pending Approvals" section</li>
                <li>Share the approval code with users</li>
              </>
            )}
          </ol>
        </div>
      </section>
    </div>
  );
}
