import React, { useState, useEffect } from 'react';
import { getRegistrationByToken, cancelRegistration, RegistrationItem } from '../api/client.ts';

interface Props {
  token: string;
  onDone: () => void;
}

export const CancelView: React.FC<Props> = ({ token, onDone }) => {
  const [loading, setLoading] = useState(true);
  const [cancelling, setCancelling] = useState(false);
  const [registration, setRegistration] = useState<RegistrationItem | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    getRegistrationByToken(token)
      .then((data) => setRegistration(data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token]);

  const handleConfirmCancel = async () => {
    setCancelling(true);
    setError(null);
    try {
      const res = await cancelRegistration(token);
      setSuccessMessage(res.message);
      setRegistration((prev) => (prev ? { ...prev, status: 'cancelled' } : null));
    } catch (err: any) {
      setError(err.message || 'Ошибка отмены');
    } finally {
      setCancelling(false);
    }
  };

  if (loading) {
    return <div className="card">Загрузка информации о регистрации...</div>;
  }

  if (error && !registration) {
    return (
      <div className="card">
        <div className="alert alert-error">{error}</div>
        <button onClick={onDone} className="btn btn-secondary">
          Вернуться на главную
        </button>
      </div>
    );
  }

  return (
    <div className="card">
      <h2 className="card-title">Отказ от участия в мероприятии</h2>

      {successMessage ? (
        <div>
          <div className="alert alert-success">
            {successMessage}. Место освобождено, статус обновлен.
          </div>
          <button onClick={onDone} className="btn btn-primary" style={{ marginTop: '1rem' }}>
            На главную страницу
          </button>
        </div>
      ) : registration?.status === 'cancelled' ? (
        <div>
          <div className="alert alert-warning">
            Эта регистрация уже была отменена ранее.
          </div>
          <button onClick={onDone} className="btn btn-secondary" style={{ marginTop: '1rem' }}>
            На главную
          </button>
        </div>
      ) : (
        <div>
          <p style={{ margin: '1rem 0' }}>
            Вы собираетесь отменить регистрацию для адреса <strong>{registration?.email}</strong>.
          </p>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
            Если вы отмените участие, ваше место автоматически перейдёт к первому участнику из листа ожидания.
          </p>

          {error && <div className="alert alert-error">{error}</div>}

          <div style={{ display: 'flex', gap: '1rem' }}>
            <button
              onClick={handleConfirmCancel}
              className="btn btn-danger"
              disabled={cancelling}
            >
              {cancelling ? 'Отмена...' : 'Подтвердить отказ от участия'}
            </button>
            <button onClick={onDone} className="btn btn-secondary">
              Не отменять
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
