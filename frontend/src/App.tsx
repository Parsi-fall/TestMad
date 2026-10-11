import React, { useState, useEffect } from 'react';
import { getEvents, EventItem } from './api/client.ts';
import { EventRegistration } from './components/EventRegistration.tsx';
import { CheckInScreen } from './components/CheckInScreen.tsx';
import { OrganizerDashboard } from './components/OrganizerDashboard.tsx';
import { CancelView } from './components/CancelView.tsx';

type Tab = 'register' | 'checkin' | 'organizer';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('register');
  const [event, setEvent] = useState<EventItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Check URL params for cancellation token (e.g., /?token=XYZ)
  const urlParams = new URLSearchParams(window.location.search);
  const tokenParam = urlParams.get('token');

  const fetchActiveEvent = async () => {
    try {
      setLoading(true);
      const events = await getEvents();
      if (events.length > 0) {
        setEvent(events[0]);
      } else {
        setError('Мероприятия не найдены');
      }
    } catch (err: any) {
      setError(err.message || 'Ошибка подключения к серверу');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchActiveEvent();
  }, []);

  return (
    <div className="container">
      <header className="header">
        <h1>Сервис регистрации на мероприятия</h1>
        <p>Клиент-серверная система с листом ожидания, электронными билетами и live-чекином</p>
      </header>

      {/* Direct Cancellation View if accessed via token from email */}
      {tokenParam ? (
        <CancelView
          token={tokenParam}
          onDone={() => {
            window.history.replaceState({}, '', window.location.pathname);
            fetchActiveEvent();
          }}
        />
      ) : (
        <>
          {/* Main Navigation Tabs */}
          <nav className="nav-tabs">
            <button
              className={`nav-tab ${activeTab === 'register' ? 'active' : ''}`}
              onClick={() => setActiveTab('register')}
            >
              🎟️ Регистрация участника
            </button>
            <button
              className={`nav-tab ${activeTab === 'checkin' ? 'active' : ''}`}
              onClick={() => setActiveTab('checkin')}
            >
              🛂 Чекин на входе
            </button>
            <button
              className={`nav-tab ${activeTab === 'organizer' ? 'active' : ''}`}
              onClick={() => setActiveTab('organizer')}
            >
              📊 Экран организатора (Live)
            </button>
          </nav>

          {loading && !event && <div className="card">Загрузка данных...</div>}
          {error && <div className="alert alert-error">{error}</div>}

          {/* Active Tab View */}
          {activeTab === 'register' && (
            <EventRegistration event={event} onRefresh={fetchActiveEvent} />
          )}

          {activeTab === 'checkin' && <CheckInScreen />}

          {activeTab === 'organizer' && (
            <OrganizerDashboard event={event} onRefresh={fetchActiveEvent} />
          )}
        </>
      )}
    </div>
  );
};

export default App;
