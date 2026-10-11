import React, { useState, useRef } from 'react';
import { checkinTicket, CheckInResult } from '../api/client.ts';

export const CheckInScreen: React.FC = () => {
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [successResult, setSuccessResult] = useState<CheckInResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [history, setHistory] = useState<CheckInResult[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleCheckin = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanCode = code.trim().toUpperCase();
    if (!cleanCode) return;

    setLoading(true);
    setSuccessResult(null);
    setErrorMessage(null);

    try {
      const res = await checkinTicket(cleanCode);
      setSuccessResult(res);
      setHistory((prev) => [res, ...prev.slice(0, 9)]);
      setCode('');
    } catch (err: any) {
      setErrorMessage(err.message || 'Ошибка валидации билета');
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  return (
    <div className="card">
      <h2 className="card-title">🛂 Стойка чекина (Контролёр)</h2>
      <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem', fontSize: '0.95rem' }}>
        Введите код билета с экрана участника или из письма.
      </p>

      <form onSubmit={handleCheckin} style={{ marginBottom: '1.5rem' }}>
        <div className="input-group">
          <label className="input-label" htmlFor="ticket-code-input">
            Код билета (например, TKT-8X4M9K):
          </label>
          <input
            ref={inputRef}
            id="ticket-code-input"
            type="text"
            className="input-field"
            placeholder="TKT-XXXXXX"
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            style={{
              fontFamily: 'monospace',
              fontSize: '1.25rem',
              letterSpacing: '2px',
              textTransform: 'uppercase',
            }}
            disabled={loading}
            autoFocus
          />
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          style={{ width: '100%', fontSize: '1.1rem' }}
          disabled={loading || !code.trim()}
        >
          {loading ? 'Проверка...' : 'Отметить вход (Чекин)'}
        </button>
      </form>

      {successResult && (
        <div className="alert alert-success" style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          <strong>✅ УСПЕШНЫЙ ВХОД</strong>
          <div>Участник: <strong>{successResult.attendee_email}</strong></div>
          <div>Билет: <code style={{ fontWeight: 'bold' }}>{successResult.ticket_code}</code></div>
          <div style={{ fontSize: '0.85rem', color: '#166534' }}>
            Время: {new Date(successResult.checked_in_at).toLocaleTimeString('ru-RU')}
          </div>
        </div>
      )}

      {errorMessage && (
        <div className="alert alert-error" style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          <strong>⛔ ВХОД ЗАПРЕЩЁН</strong>
          <div>{errorMessage}</div>
        </div>
      )}

      {history.length > 0 && (
        <div style={{ marginTop: '2rem' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.75rem', color: '#475569' }}>
            Недавние проходы на этой стойке:
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {history.map((item, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  background: '#f1f5f9',
                  padding: '0.6rem 0.85rem',
                  borderRadius: '6px',
                  fontSize: '0.9rem',
                }}
              >
                <span>
                  <strong>{item.attendee_email}</strong> (<code style={{ fontSize: '0.85rem' }}>{item.ticket_code}</code>)
                </span>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                  {new Date(item.checked_in_at).toLocaleTimeString('ru-RU')}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
