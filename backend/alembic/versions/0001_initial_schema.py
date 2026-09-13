"""initial schema: users, technician_profiles, diagnostic_sessions, service_dispatches

Revision ID: 0001
Revises:
Create Date: 2026-09-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import geoalchemy2

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("phone_number", sa.String(20), nullable=False, unique=True),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role IN ('CUSTOMER', 'TECHNICIAN', 'ADMIN')", name="ck_users_role"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "technician_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skills", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("is_available", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("current_location", geoalchemy2.Geometry(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("base_rating", sa.Numeric(3, 2), server_default="5.00", nullable=False),
        sa.Column("wallet_balance", sa.Numeric(12, 2), server_default="0.00", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "idx_technician_location", "technician_profiles", ["current_location"], postgresql_using="gist"
    )

    op.create_table(
        "diagnostic_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("technician_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("session_status", sa.String(30), nullable=False),
        sa.Column("raw_audio_url", sa.Text(), nullable=True),
        sa.Column("voice_transcript", sa.Text(), nullable=True),
        sa.Column("ai_structured_summary", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("raw_recording_url", sa.Text(), nullable=True),
        sa.Column("hls_master_playlist_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "session_status IN ('INITIATED', 'IN_PROGRESS', 'RESOLVED_REMOTELY', 'ESCALATED_TO_DISPATCH', 'TERMINATED')",
            name="ck_diagnostic_sessions_status",
        ),
    )

    op.create_table(
        "service_dispatches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("diagnostic_sessions.id"), nullable=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("technician_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("customer_location", geoalchemy2.Geometry(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("dispatch_status", sa.String(30), nullable=False),
        sa.Column("start_otp_hash", sa.String(255), nullable=False),
        sa.Column("end_otp_hash", sa.String(255), nullable=False),
        sa.Column("parts_replaced", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("total_service_fee", sa.Numeric(10, 2), server_default="0.00", nullable=False),
        sa.Column("platform_commission_fee", sa.Numeric(10, 2), server_default="0.00", nullable=False),
        sa.Column("technician_earnings", sa.Numeric(10, 2), server_default="0.00", nullable=False),
        sa.Column("invoice_pdf_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "dispatch_status IN ('PENDING', 'ACCEPTED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')",
            name="ck_service_dispatches_status",
        ),
    )
    op.create_index(
        "idx_dispatch_location", "service_dispatches", ["customer_location"], postgresql_using="gist"
    )


def downgrade() -> None:
    op.drop_index("idx_dispatch_location", table_name="service_dispatches")
    op.drop_table("service_dispatches")
    op.drop_table("diagnostic_sessions")
    op.drop_index("idx_technician_location", table_name="technician_profiles")
    op.drop_table("technician_profiles")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
