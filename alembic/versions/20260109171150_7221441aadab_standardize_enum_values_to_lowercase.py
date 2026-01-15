"""standardize enum values to lowercase

Revision ID: 7221441aadab
Revises: e49027eaf405
Create Date: 2026-01-09 17:11:50.324991

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7221441aadab"
down_revision: str | Sequence[str] | None = "e49027eaf405"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema - standardize enum values to lowercase.

    This migration updates:
    1. user_status PostgreSQL enum (INVITED -> invited, ACTIVE -> active, SUSPENDED -> suspended)
    2. verification_code_type PostgreSQL enum (REGISTRATION -> registration, INVITE -> invite)
    3. score_flags string columns (status, flag_type, confidence) to lowercase
    """
    # Update user_status enum (PostgreSQL native enum)
    # Step 1: Drop the default first (can't change type with default in place)
    op.execute("ALTER TABLE users ALTER COLUMN status DROP DEFAULT")

    # Step 2: Create new enum type with lowercase values
    op.execute("CREATE TYPE user_status_new AS ENUM ('invited', 'active', 'suspended')")

    # Step 3: Alter column to use text temporarily
    op.execute("ALTER TABLE users ALTER COLUMN status TYPE text USING status::text")

    # Step 4: Update existing data to lowercase
    op.execute("UPDATE users SET status = LOWER(status)")

    # Step 5: Alter column to use new enum type
    op.execute(
        "ALTER TABLE users ALTER COLUMN status TYPE user_status_new USING status::user_status_new"
    )

    # Step 6: Drop old enum type and rename new one
    op.execute("DROP TYPE user_status")
    op.execute("ALTER TYPE user_status_new RENAME TO user_status")

    # Step 7: Re-add server default with new lowercase value
    op.execute("ALTER TABLE users ALTER COLUMN status SET DEFAULT 'active'::user_status")

    # Update verification_code_type enum (PostgreSQL native enum)
    # Step 1: Drop the default first
    op.execute("ALTER TABLE verification_codes ALTER COLUMN code_type DROP DEFAULT")

    # Step 2: Create new enum type with lowercase values
    op.execute("CREATE TYPE verification_code_type_new AS ENUM ('registration', 'invite')")

    # Step 3: Alter column to use text temporarily
    op.execute(
        "ALTER TABLE verification_codes ALTER COLUMN code_type TYPE text USING code_type::text"
    )

    # Step 4: Update existing data to lowercase
    op.execute("UPDATE verification_codes SET code_type = LOWER(code_type)")

    # Step 5: Alter column to use new enum type
    op.execute(
        "ALTER TABLE verification_codes ALTER COLUMN code_type TYPE verification_code_type_new "
        "USING code_type::verification_code_type_new"
    )

    # Step 6: Drop old enum type and rename new one
    op.execute("DROP TYPE verification_code_type")
    op.execute("ALTER TYPE verification_code_type_new RENAME TO verification_code_type")

    # Step 7: Re-add server default with new lowercase value
    op.execute(
        "ALTER TABLE verification_codes ALTER COLUMN code_type "
        "SET DEFAULT 'registration'::verification_code_type"
    )

    # Update score_flags string columns to lowercase (not PostgreSQL enums, just strings)
    # These are stored as VARCHAR, not PostgreSQL enum types
    op.execute("UPDATE score_flags SET status = LOWER(status)")
    op.execute("UPDATE score_flags SET flag_type = LOWER(flag_type)")
    op.execute("UPDATE score_flags SET confidence = LOWER(confidence)")


def downgrade() -> None:
    """Downgrade schema - restore uppercase enum values."""
    # Restore user_status enum to uppercase
    op.execute("ALTER TABLE users ALTER COLUMN status DROP DEFAULT")
    op.execute("CREATE TYPE user_status_new AS ENUM ('INVITED', 'ACTIVE', 'SUSPENDED')")
    op.execute("ALTER TABLE users ALTER COLUMN status TYPE text USING status::text")
    op.execute("UPDATE users SET status = UPPER(status)")
    op.execute(
        "ALTER TABLE users ALTER COLUMN status TYPE user_status_new USING status::user_status_new"
    )
    op.execute("DROP TYPE user_status")
    op.execute("ALTER TYPE user_status_new RENAME TO user_status")
    op.execute("ALTER TABLE users ALTER COLUMN status SET DEFAULT 'ACTIVE'::user_status")

    # Restore verification_code_type enum to uppercase
    op.execute("ALTER TABLE verification_codes ALTER COLUMN code_type DROP DEFAULT")
    op.execute("CREATE TYPE verification_code_type_new AS ENUM ('REGISTRATION', 'INVITE')")
    op.execute(
        "ALTER TABLE verification_codes ALTER COLUMN code_type TYPE text USING code_type::text"
    )
    op.execute("UPDATE verification_codes SET code_type = UPPER(code_type)")
    op.execute(
        "ALTER TABLE verification_codes ALTER COLUMN code_type TYPE verification_code_type_new "
        "USING code_type::verification_code_type_new"
    )
    op.execute("DROP TYPE verification_code_type")
    op.execute("ALTER TYPE verification_code_type_new RENAME TO verification_code_type")
    op.execute(
        "ALTER TABLE verification_codes ALTER COLUMN code_type "
        "SET DEFAULT 'REGISTRATION'::verification_code_type"
    )

    # Restore score_flags string columns to uppercase
    op.execute("UPDATE score_flags SET status = UPPER(status)")
    op.execute("UPDATE score_flags SET flag_type = UPPER(flag_type)")
    op.execute("UPDATE score_flags SET confidence = UPPER(confidence)")
