"""Modelos para Notas Fiscais processadas pelo n8n"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class NotaFiscal(Base):
    """
    Tabela de notas fiscais processadas pelo n8n
    Populada automaticamente pelo n8n após processamento dos arquivos
    Modelo padronizado sem redundâncias
    """
    __tablename__ = "notas_fiscais"

    id = Column(Integer, primary_key=True, index=True)

    # Dados da nota fiscal
    numero = Column(String(50), nullable=False, index=True)
    serie = Column(String(10), nullable=False)
    chave_acesso = Column(String(44), nullable=True, index=True)  # Chave única da NFe

    # Fornecedor
    cnpj_fornecedor = Column(String(18), nullable=False, index=True)
    nome_fornecedor = Column(String(255), nullable=False)

    # Valores
    valor_total = Column(DECIMAL(15, 2), nullable=False)  # Valor total da NF
    valor_produtos = Column(DECIMAL(15, 2), nullable=True)  # Valor dos produtos/serviços
    valor_impostos = Column(DECIMAL(15, 2), nullable=True, default=0)  # Total de impostos
    valor_frete = Column(DECIMAL(15, 2), nullable=True, default=0)  # Valor do frete

    # Datas
    data_emissao = Column(DateTime, nullable=False, index=True)
    data_entrada = Column(DateTime, nullable=True)

    # Organização por pastas (do n8n)
    pasta_origem = Column(String(255), nullable=False, index=True)  # Nome da pasta original
    subpasta = Column(String(255), nullable=True, index=True)  # Subpasta se houver

    # Status e controle
    status_processamento = Column(String(50), nullable=False, default='processado', index=True)  # processado, erro, validado
    observacoes = Column(Text, nullable=True)

    # Relacionamentos com contratos e ordens de compra
    contrato_id = Column(Integer, ForeignKey("contracts.id"), nullable=True, index=True)
    ordem_compra_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True, index=True)

    # Auditoria
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    processed_by_n8n_at = Column(DateTime(timezone=True), nullable=True)

    # Relacionamentos
    itens = relationship("NotaFiscalItem", back_populates="nota_fiscal", cascade="all, delete-orphan", primaryjoin="NotaFiscal.id == NotaFiscalItem.nota_id")
    contrato = relationship(
        "Contract",
        primaryjoin="foreign(NotaFiscal.contrato_id) == Contract.id",
        back_populates="notas_fiscais"
    )
    ordem_compra = relationship("PurchaseOrder", foreign_keys=[ordem_compra_id])

    def __repr__(self):
        return f"<NotaFiscal(numero={self.numero}, fornecedor={self.nome_fornecedor})>"


class NotaFiscalItem(Base):
    """
    Itens das notas fiscais processadas pelo n8n
    Cada item representa um produto/serviço da nota fiscal
    """
    __tablename__ = "nf_itens"

    id = Column(Integer, primary_key=True, index=True)
    nota_id = Column(Integer, ForeignKey("notas_fiscais.id"), nullable=False, index=True)

    # Dados do item
    numero_item = Column(Integer, nullable=False)  # Sequencial do item na NF
    codigo_produto = Column(String(60), nullable=True)
    descricao = Column(Text, nullable=False)
    ncm = Column(String(10), nullable=True)

    # Quantidades e medidas
    quantidade = Column(DECIMAL(15, 4), nullable=False)
    unidade = Column(String(10), nullable=False, default='UN')
    valor_unitario = Column(DECIMAL(15, 4), nullable=False)
    valor_total = Column(DECIMAL(15, 2), nullable=False)

    # Peso (se aplicável)
    peso_liquido = Column(DECIMAL(15, 4), nullable=True)
    peso_bruto = Column(DECIMAL(15, 4), nullable=True)

    # Classificação e integração
    centro_custo_id = Column(Integer, ForeignKey("cost_centers.id"), nullable=True, index=True)
    item_orcamento_id = Column(Integer, nullable=True, index=True)  # Referência ao item do orçamento

    # Scores de classificação (IA/matching)
    score_classificacao = Column(DECIMAL(5, 2), nullable=True)  # 0-100
    fonte_classificacao = Column(String(20), nullable=True)  # 'ai', 'manual', 'auto'

    # Status do item
    status_integracao = Column(String(20), nullable=False, default='pendente')  # pendente, integrado, erro
    integrado_em = Column(DateTime, nullable=True)

    # Auditoria
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relacionamentos
    nota_fiscal = relationship("NotaFiscal", back_populates="itens")
    centro_custo = relationship("CostCenter", foreign_keys=[centro_custo_id])

    def __repr__(self):
        return f"<NotaFiscalItem(descricao={self.descricao[:50]}, valor={self.valor_total})>"


class ProcessamentoLog(Base):
    """
    Log de processamentos do n8n para auditoria
    """
    __tablename__ = "processamento_logs"

    id = Column(Integer, primary_key=True, index=True)
    pasta_nome = Column(String(255), nullable=False, index=True)
    webhook_chamado_em = Column(DateTime, nullable=False)
    status = Column(String(50), nullable=False)  # iniciado, concluido, erro
    quantidade_arquivos = Column(Integer, nullable=True)
    quantidade_nfs = Column(Integer, nullable=True)
    mensagem = Column(Text, nullable=True)
    detalhes_erro = Column(Text, nullable=True)

    # Auditoria
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<ProcessamentoLog(pasta={self.pasta_nome}, status={self.status})>"