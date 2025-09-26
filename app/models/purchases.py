from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    cnpj = Column(String, unique=True, index=True)
    email = Column(String)
    telefone = Column(String)
    endereco = Column(Text)
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relacionamentos
    quotations = relationship("Quotation", back_populates="supplier")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    numero_oc = Column(String, unique=True, index=True, nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    valor_total = Column(Numeric(15, 2), nullable=False)
    data_emissao = Column(DateTime(timezone=True), nullable=False)
    data_entrega_prevista = Column(DateTime(timezone=True))
    data_entrega_real = Column(DateTime(timezone=True))
    status = Column(String, default="pendente")  # pendente, aprovada, entregue, cancelada
    observacoes = Column(Text)
    justificativa_escolha = Column(Text)
    criado_por = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relacionamentos
    contract = relationship("Contract", back_populates="purchase_orders")
    supplier = relationship("Supplier")
    creator = relationship("User", foreign_keys=[criado_por])
    items = relationship("PurchaseOrderItem", back_populates="purchase_order")
    quotations = relationship("Quotation", back_populates="purchase_order")
    invoices = relationship("Invoice", back_populates="purchase_order")


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id = Column(Integer, primary_key=True, index=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    budget_item_id = Column(Integer, ForeignKey("budget_items.id"))
    descricao = Column(Text, nullable=False)
    centro_custo = Column(String, nullable=False)
    unidade = Column(String)
    quantidade = Column(Numeric(15, 4))
    peso = Column(Numeric(15, 4))
    valor_unitario = Column(Numeric(15, 2))
    valor_total = Column(Numeric(15, 2), nullable=False)
    # Para serviços
    horas_normais = Column(Numeric(10, 2))
    horas_extras = Column(Numeric(10, 2))
    salario = Column(Numeric(15, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relacionamentos
    purchase_order = relationship("PurchaseOrder", back_populates="items")
    budget_item = relationship("BudgetItem")


class Quotation(Base):
    __tablename__ = "quotations"

    id = Column(Integer, primary_key=True, index=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    valor_total = Column(Numeric(15, 2), nullable=False)
    prazo_entrega_dias = Column(Integer)
    condicoes_pagamento = Column(String)
    observacoes = Column(Text)
    is_selected = Column(Boolean, default=False)
    data_cotacao = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relacionamentos
    purchase_order = relationship("PurchaseOrder", back_populates="quotations")
    supplier = relationship("Supplier", back_populates="quotations")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)  # Novo: vinculação direta ao contrato
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True)  # Agora opcional
    numero_nf = Column(String, nullable=False, index=True)
    fornecedor = Column(String, nullable=True)  # Novo: nome do fornecedor
    valor_total = Column(Numeric(15, 2), nullable=False)
    data_emissao = Column(DateTime(timezone=True), nullable=False)
    data_vencimento = Column(DateTime(timezone=True))
    data_pagamento = Column(DateTime(timezone=True))
    arquivo_original = Column(String, nullable=True)  # Novo: path/URL do arquivo original
    observacoes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relacionamentos
    contract = relationship("Contract", back_populates="invoices")  # Novo relacionamento
    purchase_order = relationship("PurchaseOrder", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    descricao = Column(Text, nullable=False)
    centro_custo = Column(String, nullable=False)
    unidade = Column(String)
    quantidade = Column(Numeric(15, 4))
    peso = Column(Numeric(15, 4))
    valor_unitario = Column(Numeric(15, 2))
    valor_total = Column(Numeric(15, 2), nullable=False)
    peso_divergente = Column(Numeric(15, 4))  # Peso diferente do previsto
    valor_divergente = Column(Numeric(15, 2))  # Valor diferente do previsto
    justificativa_divergencia = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relacionamentos
    invoice = relationship("Invoice", back_populates="items")