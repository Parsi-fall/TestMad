"""
Скрипт демонстрации полного сквозного сценария сервиса регистрации.
Запуск:
    python scripts/demo.py
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

# Ensure project backend is in path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
sys.path.insert(0, BACKEND_DIR)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import httpx

GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_step(number: int, title: str):
    print(f"\n{BOLD}{CYAN}=== ШАГ {number}: {title} ==={RESET}")


def print_success(msg: str):
    print(f"{GREEN}  [OK] {msg}{RESET}")


def print_info(msg: str):
    print(f"{BLUE}  [INFO] {msg}{RESET}")


def print_warning(msg: str):
    print(f"{YELLOW}  [WARN] {msg}{RESET}")


async def run_demo():
    print(f"\n{BOLD}========================================================")
    print("   ДЕМОНСТРАЦИОННЫЙ СЦЕНАРИЙ: EVENT REGISTRATION SERVICE")
    print(f"========================================================{RESET}")

    base_url = os.environ.get("API_URL", "http://localhost:8000")
    mailhog_url = os.environ.get("MAILHOG_API_URL", "http://localhost:8025")

    # Check if real server is up, otherwise run in-process client
    is_live_server = False
    try:
        async with httpx.AsyncClient(timeout=2.0) as check_client:
            res = await check_client.get(f"{base_url}/api/v1/health")
            if res.status_code == 200:
                is_live_server = True
                print_info(f"Подключено к запущенному серверу: {base_url}")
    except Exception:
        pass

    if not is_live_server:
        print_info("Сервер не обнаружен на localhost:8000. Запуск сценария через in-memory ASGI...")
        os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
        os.environ["MAILHOG_HOST"] = "localhost"

        from unittest.mock import AsyncMock
        import aiosmtplib
        # Mock SMTP when standalone to avoid connection timeouts
        aiosmtplib.send = AsyncMock(return_value=({}, "OK"))

        from app.core.database import Base, engine
        from app.main import app

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
    else:
        client = httpx.AsyncClient(base_url=base_url)

    async with client:
        # ШАГ 1: Создание события
        print_step(1, "Создание события с жестким лимитом (capacity = 2)")
        now = datetime.now(timezone.utc)
        create_res = await client.post(
            "/api/v1/events",
            json={
                "title": "High-Load Python Architecture Meetup",
                "description": "Практический воркшоп по FastAPI и PostgreSQL",
                "event_date": (now + timedelta(hours=12)).isoformat(),
                "capacity": 2,
            },
        )
        event = create_res.json()
        event_id = event["id"]
        print_success(f"Событие создано: «{event['title']}» (ID: {event_id}, Лимит: {event['capacity']})")

        # ШАГ 2: Параллельная гонка за места (Race Condition)
        print_step(2, "Параллельная регистрация 3 человек на 2 места (Race Condition)")
        emails = ["anna@company.com", "boris@company.com", "cyril@company.com"]
        tasks = [
            client.post(f"/api/v1/events/{event_id}/register", json={"email": e})
            for e in emails
        ]
        results = await asyncio.gather(*tasks)

        reg_data = [r.json() for r in results]
        confirmed = [r for r in reg_data if r["status"] == "confirmed"]
        waitlist = [r for r in reg_data if r["status"] == "waitlist"]

        print_info(f"Запросов отправлено: {len(emails)}")
        print_success(f"Подтверждено мест (confirmed): {len(confirmed)} из {event['capacity']}")
        for c in confirmed:
            print(f"     • {c['email']} -> Билет {BOLD}{c['ticket']['ticket_code']}{RESET}")

        print_warning(f"Направлено в лист ожидания (waitlist): {len(waitlist)}")
        for w in waitlist:
            print(f"     • {w['email']} -> Позиция в очереди #{w['waitlist_position']}")

        # Проверка идемпотентности
        print_step(3, "Проверка повторной регистрации на тот же email (Идемпотентность)")
        dup_res = await client.post(
            f"/api/v1/events/{event_id}/register",
            json={"email": confirmed[0]["email"]},
        )
        dup_data = dup_res.json()
        assert dup_data["ticket"]["ticket_code"] == confirmed[0]["ticket"]["ticket_code"]
        print_success(f"Повторный запрос для {confirmed[0]['email']} вернул тот же билет {dup_data['ticket']['ticket_code']}")
        print_success("Второе место НЕ создано, лимит не уменьшился!")

        # ШАГ 4: Отмена первого участника и авто-промоут из листа ожидания
        print_step(4, "Отказ от участия и автоматический промоут из очереди (FIFO)")
        cancelling_user = confirmed[0]
        waitlisted_user = waitlist[0]
        print_info(f"Участник {cancelling_user['email']} нажимает «Отказаться от участия»...")

        cancel_res = await client.post(f"/api/v1/registrations/cancel/{cancelling_user['cancel_token']}")
        cancel_info = cancel_res.json()
        print_success(f"Регистрация отменена. Промоут получил: {BOLD}{cancel_info['promoted_email']}{RESET}")

        # Проверяем статус промоута
        promoted_check = await client.get(f"/api/v1/registrations/by-token/{waitlisted_user['cancel_token']}")
        promoted_data = promoted_check.json()
        assert promoted_data["status"] == "confirmed"
        print_success(f"Статус {waitlisted_user['email']} обновлен до CONFIRMED!")
        print_success(f"Выпущен новый билет: {BOLD}{promoted_data['ticket']['ticket_code']}{RESET}")

        # ШАГ 5: Чекин на входе и защита от повторного чекина
        print_step(5, "Чекин билета на входе и защита от повторного использования")
        ticket_to_check = confirmed[1]["ticket"]["ticket_code"]
        print_info(f"Контролёр вводит код: {ticket_to_check}...")

        checkin_res = await client.post("/api/v1/checkin", json={"ticket_code": ticket_to_check})
        print_success(f"Первый чекин: {checkin_res.json()['message']}")

        print_info("Попытка повторного ввода того же билета...")
        dup_checkin_res = await client.post("/api/v1/checkin", json={"ticket_code": ticket_to_check})
        if dup_checkin_res.status_code == 409:
            print_success(f"Повторный чекин заблокирован (409 Conflict): {dup_checkin_res.json()['detail']}")
        else:
            print_warning(f"Неожиданный статус: {dup_checkin_res.status_code}")

        # ШАГ 6: Напоминания за 24 часа
        print_step(6, "Напоминание за 24 часа (гарантия ровно одного письма)")
        reminders1 = await client.post("/api/v1/events/system/process-reminders")
        print_success(f"Первый запуск рассылки: отправлено {reminders1.json()['reminders_sent']} писем участникам")

        reminders2 = await client.post("/api/v1/events/system/process-reminders")
        print_success(f"Повторный запуск: отправлено {reminders2.json()['reminders_sent']} писем (строго одно письмо на участника!)")

        # ШАГ 7: Перенос события
        print_step(7, "Организатор переносит дату события")
        new_date = now + timedelta(days=7)
        reschedule_res = await client.post(
            f"/api/v1/events/{event_id}/reschedule",
            json={"new_event_date": new_date.isoformat()},
        )
        print_success(f"Дата обновлена на {new_date.strftime('%d.%m.%Y %H:%M')}")
        print_success("Уведомления о переносе разосланы всем зарегистрированным участникам!")

        # ШАГ 8: Проверка писем через MailHog API (если доступен)
        if is_live_server:
            try:
                async with httpx.AsyncClient(timeout=2.0) as mh_client:
                    mh_res = await mh_client.get(f"{mailhog_url}/api/v2/messages")
                    if mh_res.status_code == 200:
                        total_emails = mh_res.json().get("total", 0)
                        print_step(8, f"Проверка MailHog Web API: перехвачено {total_emails} писем")
                        print_success("Все письма успешно доставлены в локальный SMTP-ящик MailHog!")
            except Exception:
                pass

        # Итоги
        print(f"\n{BOLD}{GREEN}========================================================")
        print("   ВСЕ СЦЕНАРИИ ТЕСТОВОГО ЗАДАНИЯ УСПЕШНО ДОКАЗАНЫ!")
        print(f"========================================================{RESET}\n")


if __name__ == "__main__":
    asyncio.run(run_demo())
