"""standardize_notas_fiscais_remove_redundant_fields

Revision ID: 2575a27aa575
Revises: e729315cda78
Create Date: 2025-09-26 08:59:35.704916

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2575a27aa575'
down_revision = 'e729315cda78'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Padroniza a tabela notas_fiscais removendo campos redundantes
    e preservando os dados existentes
    """

    # Primeiro, migrar dados dos campos redundantes antes de removê-los
    print("Migrando dados de campos redundantes...")

    # 1. Migrar chave_nfe para chave_acesso (se existir)
    connection = op.get_bind()

    # Verificar se as colunas existem antes de fazer a migração
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('notas_fiscais')]

    # Adicionar coluna chave_acesso se não existir
    if 'chave_acesso' not in columns:
        op.add_column('notas_fiscais', sa.Column('chave_acesso', sa.String(length=44), nullable=True))

    # Migrar dados se as colunas existirem (limitar a 44 caracteres)
    if 'chave_nfe' in columns:
        connection.execute(sa.text("""
            UPDATE notas_fiscais
            SET chave_acesso = LEFT(chave_nfe, 44)
            WHERE chave_acesso IS NULL AND chave_nfe IS NOT NULL
        """))

    # 2. Migrar id_contracts para contrato_id
    if 'id_contracts' in columns and 'contrato_id' in columns:
        connection.execute(sa.text("""
            UPDATE notas_fiscais
            SET contrato_id = id_contracts
            WHERE contrato_id IS NULL AND id_contracts IS NOT NULL
        """))

    # 3. Migrar valor_nf para valor_total
    if 'valor_nf' in columns:
        connection.execute(sa.text("""
            UPDATE notas_fiscais
            SET valor_total = valor_nf
            WHERE valor_total IS NULL AND valor_nf IS NOT NULL
        """))

    # 4. Migrar sub_pasta para subpasta
    if 'sub_pasta' in columns and 'subpasta' in columns:
        connection.execute(sa.text("""
            UPDATE notas_fiscais
            SET subpasta = sub_pasta
            WHERE subpasta IS NULL AND sub_pasta IS NOT NULL
        """))

    # 5. Migrar dados de emitente para fornecedor (se fornecedor estiver vazio)
    if 'cnpj_emitente' in columns and 'nome_emitente' in columns:
        connection.execute(sa.text("""
            UPDATE notas_fiscais
            SET cnpj_fornecedor = cnpj_emitente, nome_fornecedor = nome_emitente
            WHERE (cnpj_fornecedor IS NULL OR cnpj_fornecedor = '')
            AND cnpj_emitente IS NOT NULL
        """))

    # Garantir que campos obrigatórios não sejam nulos
    print("Definindo valores padrão para campos obrigatórios...")
    connection.execute(sa.text("""
        UPDATE notas_fiscais
        SET status_processamento = 'processado'
        WHERE status_processamento IS NULL
    """))

    # Alterar estrutura da tabela
    print("Alterando estrutura da tabela...")

    # Alterar tipos de colunas existentes
    op.alter_column('notas_fiscais', 'numero',
               existing_type=sa.INTEGER(),
               type_=sa.String(length=50),
               existing_nullable=False)

    op.alter_column('notas_fiscais', 'serie',
               existing_type=sa.VARCHAR(length=10),
               nullable=False)

    op.alter_column('notas_fiscais', 'cnpj_fornecedor',
               existing_type=sa.VARCHAR(length=18),
               nullable=False)

    op.alter_column('notas_fiscais', 'nome_fornecedor',
               existing_type=sa.VARCHAR(length=255),
               nullable=False)

    op.alter_column('notas_fiscais', 'valor_total',
               existing_type=sa.NUMERIC(precision=15, scale=2),
               nullable=False)

    op.alter_column('notas_fiscais', 'data_emissao',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)

    op.alter_column('notas_fiscais', 'pasta_origem',
               existing_type=sa.VARCHAR(length=255),
               nullable=False)

    op.alter_column('notas_fiscais', 'status_processamento',
               existing_type=sa.VARCHAR(length=50),
               nullable=False)

    op.alter_column('notas_fiscais', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))

    # Criar índices para otimização
    print("Criando índices...")
    op.create_index(op.f('ix_notas_fiscais_chave_acesso'), 'notas_fiscais', ['chave_acesso'], unique=False)
    op.create_index(op.f('ix_notas_fiscais_created_at'), 'notas_fiscais', ['created_at'], unique=False)
    op.create_index(op.f('ix_notas_fiscais_data_emissao'), 'notas_fiscais', ['data_emissao'], unique=False)
    op.create_index(op.f('ix_notas_fiscais_numero'), 'notas_fiscais', ['numero'], unique=False)
    op.create_index(op.f('ix_notas_fiscais_status_processamento'), 'notas_fiscais', ['status_processamento'], unique=False)

    # Remover constraints antigas
    print("Removendo constraints antigas...")
    try:
        op.drop_constraint('notas_fiscais_chave_nfe_key', 'notas_fiscais', type_='unique')
    except Exception:
        pass  # Constraint pode não existir

    try:
        op.drop_constraint('notas_fiscais_id_contracts_fkey', 'notas_fiscais', type_='foreignkey')
    except Exception:
        pass  # Constraint pode não existir

    # Remover colunas redundantes
    print("Removendo colunas redundantes...")
    redundant_columns = [
        'cnpj_emitente', 'nome_emitente', 'cnpj_destinatario', 'nome_destinatario',
        'chave_nfe', 'natureza_operacao', 'tipo_nf', 'sub_pasta',
        'total_servicos', 'total_produtos', 'valor_nf', 'id_contracts'
    ]

    for column in redundant_columns:
        if column in columns:
            try:
                op.drop_column('notas_fiscais', column)
            except Exception as e:
                print(f"Aviso: Não foi possível remover coluna {column}: {e}")

    print("Migração da tabela notas_fiscais concluída!")


def downgrade() -> None:
    """
    Reverte a padronização da tabela notas_fiscais
    Restaura campos redundantes (não recomendado, dados podem ser perdidos)
    """

    print("⚠️ AVISO: O downgrade pode resultar em perda de dados")
    print("Esta operação não é recomendada em produção")

    # Remover índices criados
    op.drop_index(op.f('ix_notas_fiscais_status_processamento'), table_name='notas_fiscais')
    op.drop_index(op.f('ix_notas_fiscais_numero'), table_name='notas_fiscais')
    op.drop_index(op.f('ix_notas_fiscais_data_emissao'), table_name='notas_fiscais')
    op.drop_index(op.f('ix_notas_fiscais_created_at'), table_name='notas_fiscais')
    op.drop_index(op.f('ix_notas_fiscais_chave_acesso'), table_name='notas_fiscais')

    # Reverter alterações de tipo de coluna
    op.alter_column('notas_fiscais', 'numero',
               existing_type=sa.String(length=50),
               type_=sa.INTEGER(),
               existing_nullable=False)

    op.alter_column('notas_fiscais', 'created_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))

    # Adicionar colunas redundantes de volta (vazias)
    op.add_column('notas_fiscais', sa.Column('chave_nfe', sa.VARCHAR(length=50), nullable=True))
    op.add_column('notas_fiscais', sa.Column('id_contracts', sa.INTEGER(), nullable=True))
    op.add_column('notas_fiscais', sa.Column('valor_nf', sa.NUMERIC(precision=12, scale=2), nullable=True))
    op.add_column('notas_fiscais', sa.Column('sub_pasta', sa.TEXT(), nullable=True))

    # Migrar dados de volta (com potencial perda)
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE notas_fiscais
        SET chave_nfe = chave_acesso,
            valor_nf = valor_total,
            sub_pasta = subpasta,
            id_contracts = contrato_id
    """))

    # Remover coluna padronizada
    op.drop_column('notas_fiscais', 'chave_acesso')

    # Criar constraint antiga
    op.create_unique_constraint('notas_fiscais_chave_nfe_key', 'notas_fiscais', ['chave_nfe'])

    print("Downgrade concluído com avisos de perda de dados")