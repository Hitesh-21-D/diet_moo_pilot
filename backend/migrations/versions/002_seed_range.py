"""Support the complete unsigned 32-bit optimizer seed range."""
from alembic import op
import sqlalchemy as sa

revision = '002_seed_range'
down_revision = '001'
branch_labels = None
depends_on = None

def upgrade():
    op.alter_column('runs','seed',existing_type=sa.Integer(),type_=sa.BigInteger())

def downgrade():
    op.alter_column('runs','seed',existing_type=sa.BigInteger(),type_=sa.Integer())
