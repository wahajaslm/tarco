# WORKFLOW: Alembic migration script template for database schema changes.
# Used by: Database migration generation, schema evolution, version control
# Template variables:
# 1. ${message} - Migration description
# 2. ${up_revision} - Current revision ID
# 3. ${down_revision} - Previous revision ID
# 4. ${create_date} - Migration creation timestamp
# 5. ${upgrades} - SQL for upgrading schema
# 6. ${downgrades} - SQL for rolling back schema
#
# Migration flow: Schema change -> Generate migration -> Review -> Apply -> Verify
# This template ensures consistent migration script structure and rollback capability.

"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
