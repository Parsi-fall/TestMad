import React, { useState } from 'react';
import { EventItem, RegistrationItem, registerForEvent, cancelRegistration } from '../api/client.ts';

interface Props {
  event: EventItem | null;
  onRefresh: () => void;
}

export const EventRegistration: React.FC<Props> = ({ event, onRefresh }) => {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [registration, setRegistration] = useState<RegistrationItem | null>(null);
  const [cancelMessage, setCancelMessage] = useState<string | null>(null);

  if (!event) {
    return <div className="card">Загрузка информации о событии...</div>;
  }

  const freeSpots = Math.max(0, event.capacity - event.confirmed_count);
  const eventDateFormatted = new Date(event.event_date).toLocaleString('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;

    setLoading(true);
    setError(null);
    setCancelMessage(null);

    try {
      const res = await registerForEvent(event.id, email.trim());
      setRegistration(res);
      onRefresh();
    } catch (err: any) {
      setError(err.message || 'Ошибка при регистрации');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async () => {
    if (!registration) return;
    setLoading(true);
    try {
      const res = await cancelRegistration(registration.cancel_token);
      setCancelMessage(res.message);
      setRegistration(null);
      onRefresh();
    } catch (err: any) {
      setError(err.message || 'Ошибка отмены');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div>
          <h2 className="card-title">{event.title}</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem' }}>
            📅 {eventDateFormatted}
          </p>
        </div>
        <div>
          {freeSpots > 0 ? (
            <span className="badge badge-green">Свободно мест: {freeSpots} из {event.capacity}</span>
          ) : (
            <span className="badge badge-amber">Лист ожидания ({event.waitlist_count} в очереди)</span>
          )}
        </div>
      </div>

      {event.description && (
        <p style={{ marginTop: '1rem', color: '#334155' }}>
          {event.description}
        </p>
      )}

      {error && <div className="alert alert-error" style={{ marginTop: '1rem' }}>{error}</div>}
      {cancelMessage && <div className="alert alert-success" style={{ marginTop: '1rem' }}>{cancelMessage}</div>}

      {!registration ? (
        <form onSubmit={handleRegister} style={{ marginTop: '1.5rem' }}>
          <div className="input-group">
            <label className="input-label" htmlFor="email-input">
              Электронная почта для регистрации:
            </label>
            <input
              id="email-input"
              type="email"
              className="input-field"
              placeholder="example@mail.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={loading}
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%' }}
            disabled={loading}
          >
            {loading ? 'Регистрация...' : freeSpots > 0 ? 'Зарегистрироваться на событие' : 'Встать в лист ожидания'}
          </button>
        </form>
      ) : registration.status === 'confirmed' ? (
        <div style={{ marginTop: '1.5rem' }}>
          <div className="alert alert-success">
            🎉 Вы успешно зарегистрированы! На почту <strong>{registration.email}</strong> отправлено подтверждение.
          </div>

          {registration.ticket && (
            <div className="ticket-box">
              <span className="badge badge-green" style={{ marginBottom: '0.5rem' }}>Электронный билет</span>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Код для чекина:</p>
              <div className="ticket-code">{registration.ticket.ticket_code}</div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Покажите этот код контролёру на входе
              </p>
            </div>
          )}

          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
            <button
              onClick={() => setRegistration(null)}
              className="btn btn-secondary"
              style={{ flex: 1 }}
            >
              Зарегистрировать другого
            </button>
            <button
              onClick={handleCancel}
              className="btn btn-danger"
              style={{ flex: 1 }}
              disabled={loading}
            >
              {loading ? 'Отмена...' : 'Отказаться от участия'}
            </button>
          </div>
        </div>
      ) : (
        <div style={{ marginTop: '1.5rem' }}>
          <div className="alert alert-warning">
            ⏳ Места закончились. Вы добавлены в <strong>лист ожидания</strong> (Ваш номер: #{registration.waitlist_position || 1}).
            <br />
            Как только кто-то откажется от участия, место перейдёт к вам, и билет придёт на <strong>{registration.email}</strong>.
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
            <button
              onClick={() => setRegistration(null)}
              className="btn btn-secondary"
              style={{ flex: 1 }}
            >
              Назад
            </button>
            <button
              onClick={handleCancel}
              className="btn btn-danger"
              style={{ flex: 1 }}
              disabled={loading}
            >
              {loading ? 'Отмена...' : 'Отказаться от ожидания'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
