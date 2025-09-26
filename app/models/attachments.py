from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class AttachmentType(str, enum.Enum):
    CERTIFICADO = "certificado"
    COMPROVANTE_ENTREGA = "comprovante_entrega"
    RELATORIO_QUALIDADE = "relatorio_qualidade"
    COTACAO = "cotacao"
    NOTA_FISCAL = "nota_fiscal"
    ORDEM_COMPRA = "ordem_compra"
    PLANILHA_ORCAMENTO = "planilha_orcamento"
    OUTROS = "outros"


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String, nullable=False)
    attachment_type = Column(Enum(AttachmentType), nullable=False)
    description = Column(Text)
    version = Column(Integer, default=1)
    
    # Relacionamentos polimórficos
    entity_type = Column(String, nullable=False)  # contract, purchase_order, quotation, etc.
    entity_id = Column(Integer, nullable=False)
    
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relacionamentos
    uploader = relationship("User")