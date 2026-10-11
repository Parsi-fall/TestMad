"""initial schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-10-11 21:32:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create events table
    op.create_table(
        'events',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('event_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('capacity', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('capacity > 0', name='chk_event_capacity_positive'),
        sa.PrimaryKeyConstraint('id'),
    )

    # 2. Create registrations table
    op.create_table(
        'registrations',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('event_id', sa.Uuid(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('cancel_token', sa.String(length=64), nullable=False),
        sa.Column('reminder_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cancel_token', name='uq_registrations_cancel_token'),
        sa.UniqueConstraint('event_id', 'email', name='uq_registrations_event_email'),
    )
    op.create_index(
        'ix_registrations_event_status_created',
        'registrations',
        ['event_id', 'status', 'created_at'],
        unique=False,
    )
    op.create_index(
        'ix_registrations_cancel_token',
        'registrations',
        ['cancel_token'],
        unique=True,
    )

    # 3. Create tickets table
    op.create_table(
        'tickets',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('registration_id', sa.Uuid(), nullable=False),
        sa.Column('ticket_code', sa.String(length=16), nullable=False),
        sa.Column('is_checked_in', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('checked_in_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['registration_id'], ['registrations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('registration_id', name='uq_tickets_registration_id'),
        sa.UniqueConstraint('ticket_code', name='uq_tickets_ticket_code'),
    )
    op.create_index(
        'ix_tickets_ticket_code',
        'tickets',
        ['ticket_code'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('ix_tickets_ticket_code', table_name='tickets')
    op.drop_table('tickets')
    op.drop_index('ix_registrations_cancel_token', table_name='registrations')
    op.drop_index('ix_registrations_event_status_created', table_name='registrations')
    op.drop_table('registrations')
    op.drop_table('events')
