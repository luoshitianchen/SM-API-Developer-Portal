"""新增业务表（开发者应用 / 应用凭证 / 调用日志）

Revision ID: 0002_business_tables
Revises: 0001_initial
Create Date: 2026-09-23
"""
from __future__ import annotations
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# 本迁移由 autogenerate 生成，手动调整 revision 标识为 0002_business_tables
revision: str = '0002_business_tables'
down_revision: Union[str, None] = '0001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### 自动生成开始：创建开发者门户业务表 ###
    # 应用凭证表：存储 client_id / client_secret 哈希
    op.create_table('app_credentials',
    sa.Column('id', sa.String(length=64), nullable=False),
    sa.Column('app_id', sa.String(length=64), nullable=False),
    sa.Column('client_id', sa.String(length=64), nullable=False),
    sa.Column('client_secret_hash', sa.String(length=256), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_app_credentials_app_id'), 'app_credentials', ['app_id'], unique=False)
    op.create_index(op.f('ix_app_credentials_client_id'), 'app_credentials', ['client_id'], unique=True)
    op.create_index(op.f('ix_app_credentials_status'), 'app_credentials', ['status'], unique=False)
    # 调用日志表：记录 API 调用路径、状态码与耗时
    op.create_table('call_logs',
    sa.Column('id', sa.String(length=64), nullable=False),
    sa.Column('app_id', sa.String(length=64), nullable=False),
    sa.Column('api_path', sa.String(length=256), nullable=False),
    sa.Column('method', sa.String(length=8), nullable=False),
    sa.Column('status_code', sa.Integer(), nullable=False),
    sa.Column('latency_ms', sa.Integer(), nullable=False),
    sa.Column('called_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_call_logs_api_path'), 'call_logs', ['api_path'], unique=False)
    op.create_index(op.f('ix_call_logs_app_id'), 'call_logs', ['app_id'], unique=False)
    op.create_index(op.f('ix_call_logs_called_at'), 'call_logs', ['called_at'], unique=False)
    # 开发者应用表：开发者注册的应用基本信息
    op.create_table('developer_apps',
    sa.Column('id', sa.String(length=64), nullable=False),
    sa.Column('app_id', sa.String(length=64), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('owner', sa.String(length=128), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_developer_apps_app_id'), 'developer_apps', ['app_id'], unique=True)
    op.create_index(op.f('ix_developer_apps_status'), 'developer_apps', ['status'], unique=False)
    # ### 自动生成结束 ###


def downgrade() -> None:
    # ### 自动生成开始：回滚业务表 ###
    op.drop_index(op.f('ix_developer_apps_status'), table_name='developer_apps')
    op.drop_index(op.f('ix_developer_apps_app_id'), table_name='developer_apps')
    op.drop_table('developer_apps')
    op.drop_index(op.f('ix_call_logs_called_at'), table_name='call_logs')
    op.drop_index(op.f('ix_call_logs_app_id'), table_name='call_logs')
    op.drop_index(op.f('ix_call_logs_api_path'), table_name='call_logs')
    op.drop_table('call_logs')
    op.drop_index(op.f('ix_app_credentials_status'), table_name='app_credentials')
    op.drop_index(op.f('ix_app_credentials_client_id'), table_name='app_credentials')
    op.drop_index(op.f('ix_app_credentials_app_id'), table_name='app_credentials')
    op.drop_table('app_credentials')
    # ### 自动生成结束 ###
