import React, { useState, useEffect } from 'react';
import {
  EventItem,
  createEventWebSocket,
  rescheduleEvent,
  triggerProcessReminders,
} from '../api/client.ts';

interface Props {
  event: EventItem | null;
  onRefresh: () => void;
}

export const OrganizerDashboard: React.FC<Props> = ({ event, onRefresh }) => {
  const [liveStats, setLiveStats] = useState<{
    confirmed_count: number;
    waitlist_count: number;
    checked_in_count: number;
  } | null>(null);

  const [wsConnected, setWsConnected] = useState(false);
  const [newDateInput, setNewDateInput] = useState('');
  const [rescheduleLoading, setRescheduleLoading] = useState(false);
  const [reminderLoading, setReminderLoading] = useState(false);
  const [infoMessage, setInfoMessage] = useState<string | null>(null);

  // Connect WebSocket for real-time live counter updates
  useEffect(() => {
    if (!event) return;

    // Default to current event numbers
    setLiveStats({
      confirmed_count: event.confirmed_count,
      waitlist_count: event.waitlist_count,
      checked_in_count: event.checked_in_count,
    });

    const ws = createEventWebSocket(event.id, (data) => {
      setLiveStats({
        confirmed_count: data.confirmed_count,
        waitlist_count: data.waitlist_count,
        checked_in_count: data.checked_in_count,
      });
      setWsConnected(true);
    });

    ws.socket.onopen = () => setWsConnected(true);
    ws.socket.onclose = () => setWsConnected(false);

    return () => {
      ws.close();
    };
  }, [event?.id]);

  if (!event) {
    return <div className="card">Загрузка данных организатора...</div>;
  }

  const confirmed = liveStats ? liveStats.confirmed_count : event.confirmed_count;
  const waitlist = liveStats ? liveStats.waitlist_count : event.waitlist_count;
  const checkedIn = liveStats ? liveStats.checked_in_count : event.checked_in_count;

  const eventDateFormatted = new Date(event.event_date).toLocaleString('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  const handleReschedule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDateInput) return;

    setRescheduleLoading(true);
    setInfoMessage(null);
    try {
      const isoDate = new Date(newDateInput).toISOString();
      await rescheduleEvent(event.id, isoDate);
      setInfoMessage('Дата события успешно перенесена! Уведомления отправлены всем зарегистрированным участникам.');
      onRefresh();
    } catch (err: any) {
      setInfoMessage(`Ошибка переноса: ${err.message}`);
    } finally {
      setRescheduleLoading(false);
    }
  };

  const handleTriggerReminders = async () => {
    setReminderLoading(true);
    setInfoMessage(null);
    try {
      const res = await triggerProcessReminders();
      setInfoMessage(`Обработка завершена: отправлено напоминаний: ${res.reminders_sent}`);
    } catch (err: any) {
      setInfoMessage(`Ошибка: ${err.message}`);
    } finally {
      setReminderLoading(false);
    }
  };

  return (
    <div>
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <div>
            <h2 className="card-title" style={{ margin: 0 }}>📊 Панель организатора</h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '0.2rem' }}>
              Событие: <strong>{event.title}</strong> (Лимит: {event.capacity} мест)
            </p>
          </div>
          <div>
            {wsConnected ? (
              <span className="live-indicator">
                <span className="live-dot" /> Live (WebSocket активен)
              </span>
            ) : (
              <span className="badge badge-amber">WebSocket подключается...</span>
            )}
          </div>
        </div>

        {/* 3 Real-time Live Counters */}
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-label">ЗАРЕГИСТРИРОВАНО</div>
            <div className="stat-value" style={{ color: '#2563eb' }}>
              {confirmed} <span style={{ fontSize: '1.25rem', color: '#94a3b8' }}>/ {event.capacity}</span>
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Свободно: {Math.max(0, event.capacity - confirmed)}
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-label">В ЛИСТЕ ОЖИДАНИЯ</div>
            <div className="stat-value" style={{ color: '#d97706' }}>
              {waitlist}
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Ожидают освобождения слотов
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-label">ПРИШЛО (ЧЕКИН)</div>
            <div className="stat-value" style={{ color: '#16a34a' }}>
              {checkedIn}
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              {confirmed > 0 ? `${Math.round((checkedIn / confirmed) * 100)}% явка` : '0% явка'}
            </div>
          </div>
        </div>

        {infoMessage && <div className="alert alert-success">{infoMessage}</div>}

        {/* Reschedule Event Section */}
        <div style={{ background: '#f8fafc', padding: '1.25rem', borderRadius: '10px', border: '1px solid var(--border)', marginTop: '1.5rem' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.5rem', color: '#1e293b' }}>
            🗓️ Перенос даты события
          </h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
            Текущая дата: <strong>{eventDateFormatted}</strong>. При изменении все участники получат уведомление на почту.
          </p>

          <form onSubmit={handleReschedule} style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <input
              type="datetime-local"
              className="input-field"
              style={{ flex: 1, minWidth: '220px' }}
              value={newDateInput}
              onChange={(e) => setNewDateInput(e.target.value)}
              required
              disabled={rescheduleLoading}
            />
            <button
              type="submit"
              className="btn btn-secondary"
              disabled={rescheduleLoading || !newDateInput}
            >
              {rescheduleLoading ? 'Перенос...' : 'Перенести дату и уведомить всех'}
            </button>
          </form>
        </div>

        {/* 24h Reminder Trigger Section */}
        <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h4 style={{ fontSize: '0.95rem', fontWeight: 600 }}>⏰ Напоминания за 24 часа</h4>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Фоновый планировщик проверяет участников каждую минуту. Можно запустить проверку вручную.
            </p>
          </div>
          <button
            onClick={handleTriggerReminders}
            className="btn btn-secondary"
            disabled={reminderLoading}
          >
            {reminderLoading ? 'Проверка...' : 'Запустить рассылку напоминаний сейчас'}
          </button>
        </div>
      </div>
    </div>
  );
};
