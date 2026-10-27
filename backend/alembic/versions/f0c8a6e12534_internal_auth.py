"""Add internal credentials and hashed bearer sessions without changing legacy accounts.

Revision ID: f0c8a6e12534
Revises: e9b7f5d01423
"""

from alembic import op
import sqlalchemy as sa

revision = "f0c8a6e12534"
down_revision = "e9b7f5d01423"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("principal", sa.Column("username", sa.String(32)))
    op.add_column("principal", sa.Column("normalized_username", sa.String(32)))
    op.add_column("principal", sa.Column("password_hash", sa.Text()))
    op.add_column(
        "principal",
        sa.Column(
            "must_change_password", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )
    op.add_column(
        "principal",
        sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("principal", sa.Column("locked_at", sa.DateTime(timezone=True)))
    op.add_column("principal", sa.Column("last_login_at", sa.DateTime(timezone=True)))
    op.create_unique_constraint(
        "uq_principal_normalized_username", "principal", ["normalized_username"]
    )
    op.create_check_constraint(
        "ck_principal_failed_login_count", "principal", "failed_login_count >= 0"
    )
    op.create_check_constraint(
        "ck_principal_internal_credentials",
        "principal",
        "(username IS NULL AND normalized_username IS NULL AND password_hash IS NULL) OR "
        "(username IS NOT NULL AND normalized_username = lower(username) AND "
        "normalized_username IS NOT NULL AND password_hash IS NOT NULL)",
    )
    op.create_table(
        "auth_session",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "principal_id",
            sa.Uuid(),
            sa.ForeignKey("principal.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("token_hash", name="uq_auth_session_token_hash"),
    )
    op.create_index("ix_auth_session_principal_id", "auth_session", ["principal_id"])
    op.execute("ALTER TABLE public.auth_session ENABLE ROW LEVEL SECURITY")
    # Credentials and sessions are backend-only, including projects with Data API defaults.
    op.execute("""
        DO $internal_auth_access$
        DECLARE table_name text; data_api_role text;
        BEGIN
            FOREACH table_name IN ARRAY ARRAY['principal', 'auth_session'] LOOP
                EXECUTE format('REVOKE ALL PRIVILEGES ON TABLE public.%I FROM PUBLIC', table_name);
                FOREACH data_api_role IN ARRAY ARRAY['anon', 'authenticated'] LOOP
                    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = data_api_role) THEN
                        EXECUTE format('REVOKE ALL PRIVILEGES ON TABLE public.%I FROM %I', table_name, data_api_role);
                    END IF;
                END LOOP;
            END LOOP;
        END
        $internal_auth_access$;
    """)


def downgrade() -> None:
    # Internal sessions/credentials are discarded; Supabase identity and domain data survive.
    op.drop_table("auth_session")
    op.drop_constraint("ck_principal_internal_credentials", "principal", type_="check")
    op.drop_constraint("ck_principal_failed_login_count", "principal", type_="check")
    op.drop_constraint("uq_principal_normalized_username", "principal", type_="unique")
    for column in (
        "last_login_at",
        "locked_at",
        "failed_login_count",
        "must_change_password",
        "password_hash",
        "normalized_username",
        "username",
    ):
        op.drop_column("principal", column)
