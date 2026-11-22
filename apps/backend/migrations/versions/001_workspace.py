"""Initial private workspace schema."""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None

def upgrade():
    op.create_table('users', sa.Column('id', sa.String(36), primary_key=True), sa.Column('email', sa.String(254), nullable=False), sa.Column('password_hash', sa.Text(), nullable=False))
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_table('login_sessions', sa.Column('token_hash', sa.String(64), primary_key=True), sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False), sa.Column('expires_at', sa.Integer(), nullable=False))
    op.create_index('ix_login_sessions_user_id', 'login_sessions', ['user_id'])
    op.create_table('projects', sa.Column('id', sa.String(36), primary_key=True), sa.Column('owner_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False), sa.Column('name', sa.String(120), nullable=False), sa.Column('question', sa.Text(), nullable=False), sa.Column('audience', sa.String(200), nullable=False), sa.Column('geography', sa.String(100), nullable=False), sa.Column('created_at', sa.Integer(), nullable=False))
    op.create_index('ix_projects_owner_id', 'projects', ['owner_id'])

def downgrade():
    op.drop_table('projects')
    op.drop_table('login_sessions')
    op.drop_table('users')
