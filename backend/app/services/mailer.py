import logging
from email.message import EmailMessage
import aiosmtplib

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_email(
    to_email: str,
    subject: str,
    text_content: str,
    html_content: str,
) -> bool:
    """Send email asynchronously to MailHog."""
    message = EmailMessage()
    message["From"] = f"{settings.PROJECT_NAME} <noreply@events.local>"
    message["To"] = to_email
    message["Subject"] = subject

    message.set_content(text_content)
    message.add_alternative(html_content, subtype="html")

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.MAILHOG_HOST,
            port=settings.MAILHOG_SMTP_PORT,
            timeout=5.0,
        )
        logger.info(f"Email sent successfully to {to_email} with subject '{subject}'")
        return True
    except Exception as e:
        logger.warning(f"Failed to send email to {to_email} via MailHog: {e}")
        return False


async def send_ticket_email(
    to_email: str,
    event_title: str,
    event_date_str: str,
    ticket_code: str,
    cancel_token: str,
) -> bool:
    cancel_url = f"{settings.FRONTEND_URL}/cancel?token={cancel_token}"
    subject = f"Ваш билет на «{event_title}»"

    text = f"""Здравствуйте!

Вы успешно зарегистрированы на мероприятие: «{event_title}».
Дата и время: {event_date_str}

Ваш код билета для чекина: {ticket_code}

Если ваши планы изменятся, пожалуйста, откажитесь от участия по ссылке:
{cancel_url}

До встречи на мероприятии!
"""

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
        <h2 style="color: #2b6cb0;">Ваш электронный билет</h2>
        <p>Вы успешно зарегистрированы на событие: <strong>{event_title}</strong></p>
        <p><strong>Дата и время:</strong> {event_date_str}</p>
        
        <div style="background-color: #ebf8ff; border: 2px dashed #3182ce; border-radius: 8px; padding: 16px; margin: 20px 0; text-align: center;">
            <p style="margin: 0; font-size: 14px; color: #4a5568;">Код билета для чекина:</p>
            <h1 style="margin: 8px 0; color: #2b6cb0; letter-spacing: 4px; font-family: monospace;">{ticket_code}</h1>
            <p style="margin: 0; font-size: 12px; color: #718096;">Покажите этот код на стойке регистрации</p>
        </div>

        <p style="font-size: 14px; color: #718096; margin-top: 24px;">
            Если вы не сможете прийти, освободите место для других участников:
            <br>
            <a href="{cancel_url}" style="color: #e53e3e; text-decoration: underline;">Отказаться от участия</a>
        </p>
    </div>
    """

    return await send_email(to_email, subject, text, html)


async def send_waitlist_email(
    to_email: str,
    event_title: str,
    event_date_str: str,
    position: int,
    cancel_token: str,
) -> bool:
    cancel_url = f"{settings.FRONTEND_URL}/cancel?token={cancel_token}"
    subject = f"Вы добавлены в лист ожидания: «{event_title}»"

    text = f"""Здравствуйте!

Места на «{event_title}» закончились, но вы успешно добавлены в лист ожидания.
Ваша позиция в очереди: #{position}.

Если кто-то откажется от участия, место автоматически перейдёт к вам, и мы сразу пришлём билет на почту.

Если вы передумали, вы можете отменить заявку по ссылке:
{cancel_url}
"""

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
        <h2 style="color: #d69e2e;">Лист ожидания</h2>
        <p>Все основные места на <strong>{event_title}</strong> сейчас заняты.</p>
        <div style="background-color: #fefcbf; border: 1px solid #ecc94b; border-radius: 8px; padding: 12px; margin: 16px 0; text-align: center;">
            <p style="margin: 0; font-size: 16px;">Ваш номер в листе ожидания: <strong>#{position}</strong></p>
        </div>
        <p>Как только освободится место, система автоматически закрепит его за вами и отправит билет с кодом прохода.</p>
        <p style="font-size: 14px; color: #718096; margin-top: 24px;">
            <a href="{cancel_url}" style="color: #718096; text-decoration: underline;">Отказаться от ожидания</a>
        </p>
    </div>
    """

    return await send_email(to_email, subject, text, html)


async def send_promoted_email(
    to_email: str,
    event_title: str,
    event_date_str: str,
    ticket_code: str,
    cancel_token: str,
) -> bool:
    cancel_url = f"{settings.FRONTEND_URL}/cancel?token={cancel_token}"
    subject = f"Освободилось место! Ваш билет на «{event_title}»"

    text = f"""Отличные новости!

Участник отказался от участия, и место перешло к вам из листа ожидания на «{event_title}»!
Дата и время: {event_date_str}

Ваш код билета: {ticket_code}

Ссылка для отмены: {cancel_url}
"""

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
        <h2 style="color: #38a169;">Вам досталось место из листа ожидания!</h2>
        <p>Кто-то отказался от участия в <strong>{event_title}</strong>, и ваш статус повышен до основного участника!</p>
        
        <div style="background-color: #f0fff4; border: 2px dashed #38a169; border-radius: 8px; padding: 16px; margin: 20px 0; text-align: center;">
            <p style="margin: 0; font-size: 14px; color: #4a5568;">Код билета для чекина:</p>
            <h1 style="margin: 8px 0; color: #2f855a; letter-spacing: 4px; font-family: monospace;">{ticket_code}</h1>
        </div>

        <p style="font-size: 14px; color: #718096;">
            <a href="{cancel_url}" style="color: #e53e3e; text-decoration: underline;">Отказаться от участия</a>
        </p>
    </div>
    """

    return await send_email(to_email, subject, text, html)


async def send_reminder_email(
    to_email: str,
    event_title: str,
    event_date_str: str,
    ticket_code: str,
) -> bool:
    subject = f"Напоминание: завтра «{event_title}»"

    text = f"""Напоминание!

Мероприятие «{event_title}» состоится уже завтра ({event_date_str}).
Ваш код билета для чекина: {ticket_code}

Ждём вас!
"""

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
        <h2 style="color: #2b6cb0;">Напоминание о мероприятии</h2>
        <p>Событие <strong>{event_title}</strong> пройдёт уже завтра!</p>
        <p><strong>Дата и время:</strong> {event_date_str}</p>
        <div style="background-color: #edf2f7; border-radius: 8px; padding: 12px; margin: 16px 0; text-align: center;">
            <p style="margin: 0;">Ваш код билета: <strong style="font-family: monospace; font-size: 18px;">{ticket_code}</strong></p>
        </div>
    </div>
    """

    return await send_email(to_email, subject, text, html)


async def send_reschedule_email(
    to_email: str,
    event_title: str,
    new_date_str: str,
    ticket_code: str | None = None,
) -> bool:
    subject = f"Внимание: перенос даты мероприятия «{event_title}»"

    code_info = f"Ваш билет {ticket_code} остаётся действительным." if ticket_code else ""

    text = f"""Уважаемый участник!

Организатор перенёс дату проведения мероприятия «{event_title}».
Новая дата и время: {new_date_str}

{code_info}
"""

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
        <h2 style="color: #dd6b20;">Изменение даты мероприятия</h2>
        <p>Организатор изменил дату события <strong>{event_title}</strong>.</p>
        <p><strong>Новая дата и время:</strong> {new_date_str}</p>
        {f'<p>Ваш билет <strong>{ticket_code}</strong> остаётся в силе.</p>' if ticket_code else ''}
    </div>
    """

    return await send_email(to_email, subject, text, html)
