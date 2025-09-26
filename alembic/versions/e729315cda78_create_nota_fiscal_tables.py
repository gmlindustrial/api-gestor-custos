"""Create nota fiscal tables

Revision ID: e729315cda78
Revises: 3d3f25a66958
Create Date: 2025-09-24 12:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e729315cda78'
down_revision = '3d3f25a66958'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create processamento_logs table
    op.create_table('processamento_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pasta_nome', sa.String(length=255), nullable=False),
        sa.Column('webhook_chamado_em', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('quantidade_arquivos', sa.Integer(), nullable=True),
        sa.Column('quantidade_nfs', sa.Integer(), nullable=True),
        sa.Column('mensagem', sa.Text(), nullable=True),
        sa.Column('detalhes_erro', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_processamento_logs_id'), 'processamento_logs', ['id'], unique=False)
    op.create_index(op.f('ix_processamento_logs_pasta_nome'), 'processamento_logs', ['pasta_nome'], unique=False)

    # Update existing notas_fiscais table if it exists
    try:
        # Add new columns to existing notas_fiscais table
        op.add_column('notas_fiscais', sa.Column('chave_acesso', sa.String(length=44), nullable=True))
        op.add_column('notas_fiscais', sa.Column('cnpj_fornecedor', sa.String(length=18), nullable=True))
        op.add_column('notas_fiscais', sa.Column('nome_fornecedor', sa.String(length=255), nullable=True))
        op.add_column('notas_fiscais', sa.Column('valor_total', sa.DECIMAL(precision=15, scale=2), nullable=True))
        op.add_column('notas_fiscais', sa.Column('valor_produtos', sa.DECIMAL(precision=15, scale=2), nullable=True))
        op.add_column('notas_fiscais', sa.Column('valor_impostos', sa.DECIMAL(precision=15, scale=2), nullable=True))
        op.add_column('notas_fiscais', sa.Column('valor_frete', sa.DECIMAL(precision=15, scale=2), nullable=True))
        op.add_column('notas_fiscais', sa.Column('data_entrada', sa.DateTime(), nullable=True))
        op.add_column('notas_fiscais', sa.Column('pasta_origem', sa.String(length=255), nullable=True))
        op.add_column('notas_fiscais', sa.Column('subpasta', sa.String(length=255), nullable=True))
        op.add_column('notas_fiscais', sa.Column('status_processamento', sa.String(length=50), nullable=True))
        op.add_column('notas_fiscais', sa.Column('observacoes', sa.Text(), nullable=True))
        op.add_column('notas_fiscais', sa.Column('contrato_id', sa.Integer(), nullable=True))
        op.add_column('notas_fiscais', sa.Column('ordem_compra_id', sa.Integer(), nullable=True))
        op.add_column('notas_fiscais', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
        op.add_column('notas_fiscais', sa.Column('processed_by_n8n_at', sa.DateTime(timezone=True), nullable=True))

        # Create indexes
        op.create_index(op.f('ix_notas_fiscais_chave_acesso'), 'notas_fiscais', ['chave_acesso'], unique=False)
        op.create_index(op.f('ix_notas_fiscais_cnpj_fornecedor'), 'notas_fiscais', ['cnpj_fornecedor'], unique=False)
        op.create_index(op.f('ix_notas_fiscais_contrato_id'), 'notas_fiscais', ['contrato_id'], unique=False)
        op.create_index(op.f('ix_notas_fiscais_ordem_compra_id'), 'notas_fiscais', ['ordem_compra_id'], unique=False)
        op.create_index(op.f('ix_notas_fiscais_pasta_origem'), 'notas_fiscais', ['pasta_origem'], unique=False)
        op.create_index(op.f('ix_notas_fiscais_subpasta'), 'notas_fiscais', ['subpasta'], unique=False)

        # Create foreign keys
        op.create_foreign_key(None, 'notas_fiscais', 'contracts', ['contrato_id'], ['id'])
        op.create_foreign_key(None, 'notas_fiscais', 'purchase_orders', ['ordem_compra_id'], ['id'])

    except Exception:
        # If table doesn't exist, create it
        op.create_table('notas_fiscais',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('numero', sa.String(length=50), nullable=False),
            sa.Column('serie', sa.String(length=10), nullable=False),
            sa.Column('chave_acesso', sa.String(length=44), nullable=True),
            sa.Column('cnpj_fornecedor', sa.String(length=18), nullable=False),
            sa.Column('nome_fornecedor', sa.String(length=255), nullable=False),
            sa.Column('valor_total', sa.DECIMAL(precision=15, scale=2), nullable=False),
            sa.Column('valor_produtos', sa.DECIMAL(precision=15, scale=2), nullable=True),
            sa.Column('valor_impostos', sa.DECIMAL(precision=15, scale=2), nullable=True),
            sa.Column('valor_frete', sa.DECIMAL(precision=15, scale=2), nullable=True),
            sa.Column('data_emissao', sa.DateTime(), nullable=False),
            sa.Column('data_entrada', sa.DateTime(), nullable=True),
            sa.Column('pasta_origem', sa.String(length=255), nullable=False),
            sa.Column('subpasta', sa.String(length=255), nullable=True),
            sa.Column('status_processamento', sa.String(length=50), nullable=False),
            sa.Column('observacoes', sa.Text(), nullable=True),
            sa.Column('contrato_id', sa.Integer(), nullable=True),
            sa.Column('ordem_compra_id', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('processed_by_n8n_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['contrato_id'], ['contracts.id'], ),
            sa.ForeignKeyConstraint(['ordem_compra_id'], ['purchase_orders.id'], )
        )
        op.create_index(op.f('ix_notas_fiscais_id'), 'notas_fiscais', ['id'], unique=False)
        op.create_index(op.f('ix_notas_fiscais_numero'), 'notas_fiscais', ['numero'], unique=False)
        op.create_index(op.f('ix_notas_fiscais_chave_acesso'), 'notas_fiscais', ['chave_acesso'], unique=False)
        op.create_index(op.f('ix_notas_fiscais_cnpj_fornecedor'), 'notas_fiscais', ['cnpj_fornecedor'], unique=False)
        op.create_index(op.f('ix_notas_fiscais_contrato_id'), 'notas_fiscais', ['contrato_id'], unique=False)
        op.create_index(op.f('ix_notas_fiscais_ordem_compra_id'), 'notas_fiscais', ['ordem_compra_id'], unique=False)
        op.create_index(op.f('ix_notas_fiscais_pasta_origem'), 'notas_fiscais', ['pasta_origem'], unique=False)
        op.create_index(op.f('ix_notas_fiscais_subpasta'), 'notas_fiscais', ['subpasta'], unique=False)

    # Update existing nf_itens table if it exists
    try:
        # Add new columns to existing nf_itens table
        op.add_column('nf_itens', sa.Column('nota_fiscal_id', sa.Integer(), nullable=True))
        op.add_column('nf_itens', sa.Column('numero_item', sa.Integer(), nullable=True))
        op.add_column('nf_itens', sa.Column('ncm', sa.String(length=10), nullable=True))
        op.add_column('nf_itens', sa.Column('unidade', sa.String(length=10), nullable=True))
        op.add_column('nf_itens', sa.Column('peso_liquido', sa.DECIMAL(precision=15, scale=4), nullable=True))
        op.add_column('nf_itens', sa.Column('peso_bruto', sa.DECIMAL(precision=15, scale=4), nullable=True))
        op.add_column('nf_itens', sa.Column('centro_custo_id', sa.Integer(), nullable=True))
        op.add_column('nf_itens', sa.Column('item_orcamento_id', sa.Integer(), nullable=True))
        op.add_column('nf_itens', sa.Column('score_classificacao', sa.DECIMAL(precision=5, scale=2), nullable=True))
        op.add_column('nf_itens', sa.Column('fonte_classificacao', sa.String(length=20), nullable=True))
        op.add_column('nf_itens', sa.Column('status_integracao', sa.String(length=20), nullable=True))
        op.add_column('nf_itens', sa.Column('integrado_em', sa.DateTime(), nullable=True))
        op.add_column('nf_itens', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))

        # Create indexes and foreign keys
        op.create_index(op.f('ix_nf_itens_centro_custo_id'), 'nf_itens', ['centro_custo_id'], unique=False)
        op.create_index(op.f('ix_nf_itens_item_orcamento_id'), 'nf_itens', ['item_orcamento_id'], unique=False)
        op.create_index(op.f('ix_nf_itens_nota_fiscal_id'), 'nf_itens', ['nota_fiscal_id'], unique=False)

        op.create_foreign_key(None, 'nf_itens', 'notas_fiscais', ['nota_fiscal_id'], ['id'])
        op.create_foreign_key(None, 'nf_itens', 'cost_centers', ['centro_custo_id'], ['id'])

    except Exception:
        # If table doesn't exist, create it
        op.create_table('nf_itens',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('nota_fiscal_id', sa.Integer(), nullable=False),
            sa.Column('numero_item', sa.Integer(), nullable=False),
            sa.Column('codigo_produto', sa.String(length=60), nullable=True),
            sa.Column('descricao', sa.Text(), nullable=False),
            sa.Column('ncm', sa.String(length=10), nullable=True),
            sa.Column('quantidade', sa.DECIMAL(precision=15, scale=4), nullable=False),
            sa.Column('unidade', sa.String(length=10), nullable=False),
            sa.Column('valor_unitario', sa.DECIMAL(precision=15, scale=4), nullable=False),
            sa.Column('valor_total', sa.DECIMAL(precision=15, scale=2), nullable=False),
            sa.Column('peso_liquido', sa.DECIMAL(precision=15, scale=4), nullable=True),
            sa.Column('peso_bruto', sa.DECIMAL(precision=15, scale=4), nullable=True),
            sa.Column('centro_custo_id', sa.Integer(), nullable=True),
            sa.Column('item_orcamento_id', sa.Integer(), nullable=True),
            sa.Column('score_classificacao', sa.DECIMAL(precision=5, scale=2), nullable=True),
            sa.Column('fonte_classificacao', sa.String(length=20), nullable=True),
            sa.Column('status_integracao', sa.String(length=20), nullable=False),
            sa.Column('integrado_em', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['centro_custo_id'], ['cost_centers.id'], ),
            sa.ForeignKeyConstraint(['nota_fiscal_id'], ['notas_fiscais.id'], )
        )
        op.create_index(op.f('ix_nf_itens_id'), 'nf_itens', ['id'], unique=False)
        op.create_index(op.f('ix_nf_itens_centro_custo_id'), 'nf_itens', ['centro_custo_id'], unique=False)
        op.create_index(op.f('ix_nf_itens_item_orcamento_id'), 'nf_itens', ['item_orcamento_id'], unique=False)
        op.create_index(op.f('ix_nf_itens_nota_fiscal_id'), 'nf_itens', ['nota_fiscal_id'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_nf_itens_nota_fiscal_id'), table_name='nf_itens')
    op.drop_index(op.f('ix_nf_itens_item_orcamento_id'), table_name='nf_itens')
    op.drop_index(op.f('ix_nf_itens_id'), table_name='nf_itens')
    op.drop_index(op.f('ix_nf_itens_centro_custo_id'), table_name='nf_itens')

    # Drop foreign keys and columns
    try:
        op.drop_constraint(None, 'nf_itens', type_='foreignkey')
        op.drop_constraint(None, 'nf_itens', type_='foreignkey')

        op.drop_column('nf_itens', 'updated_at')
        op.drop_column('nf_itens', 'integrado_em')
        op.drop_column('nf_itens', 'status_integracao')
        op.drop_column('nf_itens', 'fonte_classificacao')
        op.drop_column('nf_itens', 'score_classificacao')
        op.drop_column('nf_itens', 'item_orcamento_id')
        op.drop_column('nf_itens', 'centro_custo_id')
        op.drop_column('nf_itens', 'peso_bruto')
        op.drop_column('nf_itens', 'peso_liquido')
        op.drop_column('nf_itens', 'unidade')
        op.drop_column('nf_itens', 'ncm')
        op.drop_column('nf_itens', 'numero_item')
        op.drop_column('nf_itens', 'nota_fiscal_id')
    except Exception:
        op.drop_table('nf_itens')

    # Drop notas_fiscais indexes and constraints
    op.drop_index(op.f('ix_notas_fiscais_subpasta'), table_name='notas_fiscais')
    op.drop_index(op.f('ix_notas_fiscais_pasta_origem'), table_name='notas_fiscais')
    op.drop_index(op.f('ix_notas_fiscais_ordem_compra_id'), table_name='notas_fiscais')
    op.drop_index(op.f('ix_notas_fiscais_numero'), table_name='notas_fiscais')
    op.drop_index(op.f('ix_notas_fiscais_id'), table_name='notas_fiscais')
    op.drop_index(op.f('ix_notas_fiscais_contrato_id'), table_name='notas_fiscais')
    op.drop_index(op.f('ix_notas_fiscais_cnpj_fornecedor'), table_name='notas_fiscais')
    op.drop_index(op.f('ix_notas_fiscais_chave_acesso'), table_name='notas_fiscais')

    try:
        op.drop_constraint(None, 'notas_fiscais', type_='foreignkey')
        op.drop_constraint(None, 'notas_fiscais', type_='foreignkey')

        op.drop_column('notas_fiscais', 'processed_by_n8n_at')
        op.drop_column('notas_fiscais', 'updated_at')
        op.drop_column('notas_fiscais', 'ordem_compra_id')
        op.drop_column('notas_fiscais', 'contrato_id')
        op.drop_column('notas_fiscais', 'observacoes')
        op.drop_column('notas_fiscais', 'status_processamento')
        op.drop_column('notas_fiscais', 'subpasta')
        op.drop_column('notas_fiscais', 'pasta_origem')
        op.drop_column('notas_fiscais', 'data_entrada')
        op.drop_column('notas_fiscais', 'valor_frete')
        op.drop_column('notas_fiscais', 'valor_impostos')
        op.drop_column('notas_fiscais', 'valor_produtos')
        op.drop_column('notas_fiscais', 'valor_total')
        op.drop_column('notas_fiscais', 'nome_fornecedor')
        op.drop_column('notas_fiscais', 'cnpj_fornecedor')
        op.drop_column('notas_fiscais', 'chave_acesso')
    except Exception:
        op.drop_table('notas_fiscais')

    # Drop processamento_logs
    op.drop_index(op.f('ix_processamento_logs_pasta_nome'), table_name='processamento_logs')
    op.drop_index(op.f('ix_processamento_logs_id'), table_name='processamento_logs')
    op.drop_table('processamento_logs')