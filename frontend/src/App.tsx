import React, { useState, useEffect } from 'react';

export const App: React.FC = () => {
  const [health, setHealth] = useState<string>('Проверка соединения...');
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    fetch(`${apiUrl}/api/v1/health`)
      .then((res) => res.json())
      .then((data) => setHealth(`Бэкенд доступен: ${data.service} (${data.status})`))
      .catch(() => setHealth('Бэкенд пока не запущен или недоступен'));
  }, [apiUrl]);

  return (
    <div style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
      <h1>Сервис регистрации на мероприятия</h1>
      <p style={{ marginTop: '1rem', color: '#4a5568' }}>{health}</p>
    </div>
  );
};

export default App;
