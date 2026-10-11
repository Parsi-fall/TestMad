const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_BASE = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

export interface EventItem {
  id: string;
  title: string;
  description: string | null;
  event_date: string;
  capacity: number;
  confirmed_count: number;
  waitlist_count: number;
  checked_in_count: number;
  created_at: string;
  updated_at: string;
}

export interface TicketItem {
  id: string;
  ticket_code: string;
  is_checked_in: boolean;
  checked_in_at: string | null;
  created_at: string;
}

export interface RegistrationItem {
  id: string;
  event_id: string;
  email: string;
  status: 'confirmed' | 'waitlist' | 'cancelled';
  cancel_token: string;
  cancel_url: string;
  waitlist_position: number | null;
  ticket: TicketItem | null;
  created_at: string;
}

export interface CheckInResult {
  status: string;
  message: string;
  ticket_code: string;
  attendee_email: string;
  event_title: string;
  checked_in_at: string;
}

export async function getEvents(): Promise<EventItem[]> {
  const res = await fetch(`${API_BASE}/api/v1/events`);
  if (!res.ok) throw new Error('Не удалось загрузить список событий');
  return res.json();
}

export async function getEvent(id: string): Promise<EventItem> {
  const res = await fetch(`${API_BASE}/api/v1/events/${id}`);
  if (!res.ok) throw new Error('Не удалось загрузить событие');
  return res.json();
}

export async function registerForEvent(eventId: string, email: string): Promise<RegistrationItem> {
  const res = await fetch(`${API_BASE}/api/v1/events/${eventId}/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Ошибка регистрации');
  }
  return res.json();
}

export async function getRegistrationByToken(token: string): Promise<RegistrationItem> {
  const res = await fetch(`${API_BASE}/api/v1/registrations/by-token/${token}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Регистрация не найдена');
  }
  return res.json();
}

export async function cancelRegistration(token: string): Promise<{ status: string; message: string; promoted_email?: string }> {
  const res = await fetch(`${API_BASE}/api/v1/registrations/cancel/${token}`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Ошибка отмены регистрации');
  }
  return res.json();
}

export async function checkinTicket(ticket_code: string): Promise<CheckInResult> {
  const res = await fetch(`${API_BASE}/api/v1/checkin`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ticket_code }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Ошибка чекина');
  }
  return res.json();
}

export async function rescheduleEvent(eventId: string, newDate: string): Promise<EventItem> {
  const res = await fetch(`${API_BASE}/api/v1/events/${eventId}/reschedule`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ new_event_date: newDate }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Ошибка переноса даты');
  }
  return res.json();
}

export async function triggerProcessReminders(): Promise<{ reminders_sent: number }> {
  const res = await fetch(`${API_BASE}/api/v1/events/system/process-reminders`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Ошибка запуска напоминаний');
  return res.json();
}

export function createEventWebSocket(eventId: string, onUpdate: (data: any) => void) {
  const socket = new WebSocket(`${WS_BASE}/api/v1/ws/events/${eventId}`);
  
  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onUpdate(data);
    } catch {
      // ping/pong text
    }
  };

  const pingInterval = setInterval(() => {
    if (socket.readyState === WebSocket.OPEN) {
      socket.send('ping');
    }
  }, 15000);

  return {
    socket,
    close: () => {
      clearInterval(pingInterval);
      socket.close();
    },
  };
}
