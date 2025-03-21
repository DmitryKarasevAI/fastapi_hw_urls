"""initial migration

Revision ID: d4f9b2a1c3e8
Revises:
Create Date: 2025-03-21 15:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg

# revision identifiers, used by Alembic.
revision = 'd4f9b2a1c3e8'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create the "user" table
    op.create_table(
        'user',
        sa.Column('id', pg.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('registered_at', sa.TIMESTAMP(), server_default=sa.text('now()')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('true')),
    )

    # Create the "urls" table
    op.create_table(
        'urls',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('creator_id', pg.UUID(as_uuid=True), nullable=True),
        sa.Column('full_url', sa.String(), nullable=False),
        sa.Column('short_url', sa.String(), nullable=False, unique=True),
        sa.Column('creation_time', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
    )

    # Create the "queries" table with CASCADE ondelete and onupdate for foreign keys
    op.create_table(
        'queries',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('url_id', sa.Integer(), nullable=False),
        sa.Column('full_url', sa.String(), nullable=False),
        sa.Column('short_url', sa.String(), nullable=False),
        sa.Column('access_time', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ['url_id'], ['urls.id'],
            ondelete='CASCADE', onupdate='CASCADE',
            name='fk_queries_url_id'
        ),
        sa.ForeignKeyConstraint(
            ['short_url'], ['urls.short_url'],
            ondelete='CASCADE', onupdate='CASCADE',
            name='fk_queries_short_url'
        ),
    )


def downgrade():
    op.drop_table('queries')
    op.drop_table('urls')
    op.drop_table('user')
