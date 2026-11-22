"""Persist multi-agent research runs, checkpoints, sources and usage."""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'

def upgrade():
    op.create_table('research_runs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('active_project_id', sa.String(36), unique=True, nullable=True),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('plan', sa.JSON(), nullable=True), sa.Column('brief', sa.JSON(), nullable=True),
        sa.Column('error', sa.Text(), nullable=False),
        sa.Column('created_at', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.Integer(), nullable=False),
        sa.Column('cancel_requested', sa.Integer(), nullable=False))
    op.create_index('ix_research_runs_project_id', 'research_runs', ['project_id'])
    op.create_table('agent_stages',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('run_id', sa.String(36), sa.ForeignKey('research_runs.id'), nullable=False),
        sa.Column('name', sa.String(40), nullable=False), sa.Column('status', sa.String(20), nullable=False),
        sa.Column('output', sa.JSON(), nullable=True), sa.Column('error', sa.Text(), nullable=False),
        sa.Column('started_at', sa.Integer(), nullable=False), sa.Column('finished_at', sa.Integer(), nullable=True),
        sa.UniqueConstraint('run_id', 'name'))
    op.create_index('ix_agent_stages_run_id', 'agent_stages', ['run_id'])
    op.create_table('model_calls',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('run_id', sa.String(36), sa.ForeignKey('research_runs.id'), nullable=False),
        sa.Column('role', sa.String(40), nullable=False), sa.Column('status', sa.String(20), nullable=False),
        sa.Column('usage', sa.JSON(), nullable=False), sa.Column('started_at', sa.Integer(), nullable=False),
        sa.Column('finished_at', sa.Integer(), nullable=True))
    op.create_index('ix_model_calls_run_id', 'model_calls', ['run_id'])
    op.create_table('research_sources',
        sa.Column('id', sa.String(40), primary_key=True),
        sa.Column('run_id', sa.String(36), sa.ForeignKey('research_runs.id'), nullable=False),
        sa.Column('url', sa.Text(), nullable=False), sa.Column('title', sa.Text(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False), sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('retrieved_at', sa.Integer(), nullable=False))
    op.create_index('ix_research_sources_run_id', 'research_sources', ['run_id'])

def downgrade():
    for table in ['research_sources', 'model_calls', 'agent_stages', 'research_runs']:
        op.drop_table(table)
