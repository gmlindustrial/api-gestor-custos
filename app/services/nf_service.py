"""Serviço de negócio para Notas Fiscais"""

from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, timedelta
from fastapi import HTTPException, status

from app.models.notas_fiscais import NotaFiscal, NotaFiscalItem, ProcessamentoLog
from app.models.contracts import Contract
from app.models.purchases import PurchaseOrder
from app.models.cost_centers import CostCenter
from app.schemas.notas_fiscais import (
    NotaFiscalCreate,
    NotaFiscalUpdate,
    NotaFiscalItemCreate,
    NotaFiscalItemUpdate,
    ProcessamentoLogCreate
)


class NotaFiscalService:
    def __init__(self, db: Session):
        self.db = db

    # === NOTAS FISCAIS ===

    def get_notas_fiscais(
        self,
        skip: int = 0,
        limit: int = 10,
        status_filter: Optional[str] = None,
        supplier: Optional[str] = None,
        contract_id: Optional[int] = None,
        pasta_origem: Optional[str] = None
    ) -> tuple[List[NotaFiscal], int]:
        """Lista notas fiscais com filtros e paginação"""
        query = self.db.query(NotaFiscal)

        # Aplicar filtros
        if status_filter:
            query = query.filter(NotaFiscal.status_processamento.ilike(f"%{status_filter}%"))

        if supplier:
            query = query.filter(NotaFiscal.nome_fornecedor.ilike(f"%{supplier}%"))

        if contract_id:
            query = query.filter(NotaFiscal.contrato_id == contract_id)

        if pasta_origem:
            query = query.filter(NotaFiscal.pasta_origem == pasta_origem)

        total = query.count()
        nfs = query.offset(skip).limit(limit).all()

        return nfs, total

    def get_nota_fiscal(self, nf_id: int) -> Optional[NotaFiscal]:
        """Busca uma nota fiscal específica com itens"""
        return self.db.query(NotaFiscal).filter(NotaFiscal.id == nf_id).first()

    def get_notas_fiscais_by_folder(
        self,
        folder_name: str,
        skip: int = 0,
        limit: int = 10
    ) -> tuple[List[NotaFiscal], int]:
        """Lista notas fiscais por pasta de origem"""
        query = self.db.query(NotaFiscal).filter(NotaFiscal.pasta_origem == folder_name)
        total = query.count()
        nfs = query.offset(skip).limit(limit).all()
        return nfs, total

    def create_nota_fiscal(self, nf_data: NotaFiscalCreate) -> NotaFiscal:
        """Cria uma nova nota fiscal com itens"""
        # Verificar se já existe nota com mesmo número e série
        existing_nf = self.db.query(NotaFiscal).filter(
            and_(
                NotaFiscal.numero == nf_data.numero,
                NotaFiscal.serie == nf_data.serie
            )
        ).first()

        if existing_nf:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Nota fiscal {nf_data.numero}/{nf_data.serie} já existe"
            )

        # Criar nota fiscal
        nf_dict = nf_data.dict(exclude={'itens'})
        nf = NotaFiscal(**nf_dict)

        self.db.add(nf)
        self.db.commit()
        self.db.refresh(nf)

        # Criar itens se fornecidos
        if nf_data.itens:
            for item_data in nf_data.itens:
                item_dict = item_data.dict()
                item_dict['nota_fiscal_id'] = nf.id
                item = NotaFiscalItem(**item_dict)
                self.db.add(item)

            self.db.commit()
            self.db.refresh(nf)

        return nf

    def update_nota_fiscal(self, nf_id: int, nf_data: NotaFiscalUpdate) -> Optional[NotaFiscal]:
        """Atualiza uma nota fiscal existente"""
        nf = self.db.query(NotaFiscal).filter(NotaFiscal.id == nf_id).first()
        if not nf:
            return None

        # Atualizar campos fornecidos
        for field, value in nf_data.dict(exclude_unset=True).items():
            setattr(nf, field, value)

        nf.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(nf)

        return nf

    def delete_nota_fiscal(self, nf_id: int) -> bool:
        """Remove uma nota fiscal e seus itens"""
        nf = self.db.query(NotaFiscal).filter(NotaFiscal.id == nf_id).first()
        if not nf:
            return False

        self.db.delete(nf)
        self.db.commit()
        return True

    # === ITENS DE NOTA FISCAL ===

    def get_item_nota_fiscal(self, item_id: int) -> Optional[NotaFiscalItem]:
        """Busca um item específico da nota fiscal"""
        return self.db.query(NotaFiscalItem).filter(NotaFiscalItem.id == item_id).first()

    def update_item_nota_fiscal(
        self,
        item_id: int,
        item_data: NotaFiscalItemUpdate
    ) -> Optional[NotaFiscalItem]:
        """Atualiza um item da nota fiscal"""
        item = self.db.query(NotaFiscalItem).filter(NotaFiscalItem.id == item_id).first()
        if not item:
            return None

        # Atualizar campos fornecidos
        for field, value in item_data.dict(exclude_unset=True).items():
            setattr(item, field, value)

        item.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(item)

        return item

    def integrate_item_to_contract(self, item_id: int, contrato_id: int, item_orcamento_id: int) -> bool:
        """Integra um item da NF com um item do orçamento do contrato"""
        item = self.db.query(NotaFiscalItem).filter(NotaFiscalItem.id == item_id).first()
        if not item:
            return False

        # Verificar se o contrato existe
        contract = self.db.query(Contract).filter(Contract.id == contrato_id).first()
        if not contract:
            return False

        # Atualizar item com integração
        item.item_orcamento_id = item_orcamento_id
        item.status_integracao = 'integrado'
        item.integrado_em = datetime.now()
        item.updated_at = datetime.now()

        # Atualizar nota fiscal com contrato
        if item.nota_fiscal.contrato_id != contrato_id:
            item.nota_fiscal.contrato_id = contrato_id
            item.nota_fiscal.updated_at = datetime.now()

        self.db.commit()
        return True

    # === ESTATÍSTICAS ===

    def get_statistics(self) -> Dict[str, Any]:
        """Calcula estatísticas das notas fiscais"""

        # Estatísticas básicas
        total_nfs = self.db.query(NotaFiscal).count()

        # Distribuição por status
        status_counts = self.db.query(
            NotaFiscal.status_processamento,
            func.count(NotaFiscal.id).label('count')
        ).group_by(NotaFiscal.status_processamento).all()

        status_distribution = {status: count for status, count in status_counts}

        # Valor total
        total_value_result = self.db.query(func.sum(NotaFiscal.valor_total)).scalar()
        total_value = float(total_value_result) if total_value_result else 0

        # Estatísticas mensais dos últimos 12 meses
        twelve_months_ago = datetime.now() - timedelta(days=365)

        monthly_stats = self.db.query(
            extract('month', NotaFiscal.data_emissao).label('month'),
            extract('year', NotaFiscal.data_emissao).label('year'),
            func.count(NotaFiscal.id).label('count'),
            func.sum(NotaFiscal.valor_total).label('value')
        ).filter(
            NotaFiscal.data_emissao >= twelve_months_ago
        ).group_by(
            extract('month', NotaFiscal.data_emissao),
            extract('year', NotaFiscal.data_emissao)
        ).order_by(
            extract('year', NotaFiscal.data_emissao).desc(),
            extract('month', NotaFiscal.data_emissao).desc()
        ).all()

        # Converter nomes dos meses
        month_names = {
            1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
            7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
        }

        monthly_data = []
        for month, year, count, value in monthly_stats:
            monthly_data.append({
                "month": month_names.get(int(month), f"Mês {month}"),
                "year": int(year),
                "count": count,
                "value": float(value) if value else 0
            })

        return {
            "total_nfs": total_nfs,
            "pending_validation": status_distribution.get("processado", 0),
            "validated": status_distribution.get("validado", 0),
            "rejected": status_distribution.get("erro", 0),
            "total_value": total_value,
            "monthly_stats": monthly_data,
            "status_distribution": status_distribution
        }

    def get_nfs_by_contract(self, contract_id: int) -> List[NotaFiscal]:
        """Lista todas as notas fiscais de um contrato"""
        return self.db.query(NotaFiscal).filter(
            NotaFiscal.contrato_id == contract_id
        ).all()

    def calculate_contract_realized_value(self, contract_id: int) -> Decimal:
        """Calcula o valor realizado de um contrato baseado nas NFs integradas"""
        result = self.db.query(func.sum(NotaFiscal.valor_total)).filter(
            and_(
                NotaFiscal.contrato_id == contract_id,
                NotaFiscal.status_processamento == 'validado'
            )
        ).scalar()

        return Decimal(result) if result else Decimal('0.00')

    # === PROCESSAMENTO LOGS ===

    def create_processing_log(self, log_data: ProcessamentoLogCreate) -> ProcessamentoLog:
        """Cria um log de processamento"""
        log = ProcessamentoLog(**log_data.dict())
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_processing_logs(
        self,
        skip: int = 0,
        limit: int = 10,
        pasta_nome: Optional[str] = None
    ) -> tuple[List[ProcessamentoLog], int]:
        """Lista logs de processamento com filtros"""
        query = self.db.query(ProcessamentoLog)

        if pasta_nome:
            query = query.filter(ProcessamentoLog.pasta_nome == pasta_nome)

        query = query.order_by(ProcessamentoLog.created_at.desc())

        total = query.count()
        logs = query.offset(skip).limit(limit).all()

        return logs, total

    def update_processing_log(
        self,
        log_id: int,
        status: str,
        mensagem: Optional[str] = None,
        detalhes_erro: Optional[str] = None,
        quantidade_arquivos: Optional[int] = None,
        quantidade_nfs: Optional[int] = None
    ) -> Optional[ProcessamentoLog]:
        """Atualiza um log de processamento"""
        log = self.db.query(ProcessamentoLog).filter(ProcessamentoLog.id == log_id).first()
        if not log:
            return None

        log.status = status
        if mensagem is not None:
            log.mensagem = mensagem
        if detalhes_erro is not None:
            log.detalhes_erro = detalhes_erro
        if quantidade_arquivos is not None:
            log.quantidade_arquivos = quantidade_arquivos
        if quantidade_nfs is not None:
            log.quantidade_nfs = quantidade_nfs

        log.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(log)

        return log

    # === CLASSIFICAÇÃO E IA ===

    def classify_item_cost_center(self, item_id: int, description: str) -> Optional[int]:
        """Classifica automaticamente um item em centro de custo baseado na descrição"""
        # Lógica simples de classificação por palavras-chave
        cost_center_keywords = {
            "materia_prima": ["cimento", "concreto", "areia", "brita", "cal", "gesso"],
            "mao_de_obra": ["servico", "mao", "obra", "trabalhador", "pedreiro"],
            "equipamento": ["equipamento", "ferramenta", "maquina", "betoneira"],
            "transporte": ["frete", "transporte", "entrega", "logistica"]
        }

        description_lower = description.lower()
        best_match = None
        best_score = 0

        for center_code, keywords in cost_center_keywords.items():
            score = sum(1 for keyword in keywords if keyword in description_lower)
            if score > best_score:
                best_score = score
                best_match = center_code

        if best_match and best_score > 0:
            # Buscar centro de custo no banco
            center = self.db.query(CostCenter).filter(
                CostCenter.codigo == best_match
            ).first()

            if center:
                # Atualizar item com classificação
                item = self.db.query(NotaFiscalItem).filter(
                    NotaFiscalItem.id == item_id
                ).first()

                if item:
                    item.centro_custo_id = center.id
                    item.score_classificacao = Decimal(str(min(95, best_score * 20)))
                    item.fonte_classificacao = 'ai'
                    item.updated_at = datetime.now()
                    self.db.commit()
                    return center.id

        return None

    # === KPIS AGREGADOS ===

    def calculate_global_kpis(self) -> Dict[str, Any]:
        """Calcula KPIs globais baseados em todas as NFs e contratos"""

        # Total de NFs por status
        total_nfs = self.db.query(NotaFiscal).count()
        nfs_validadas = self.db.query(NotaFiscal).filter(
            NotaFiscal.status_processamento == 'validado'
        ).count()
        nfs_pendentes = self.db.query(NotaFiscal).filter(
            NotaFiscal.status_processamento == 'processado'
        ).count()
        nfs_erro = self.db.query(NotaFiscal).filter(
            NotaFiscal.status_processamento == 'erro'
        ).count()

        # Valor total das NFs validadas
        total_valor_validado = self.db.query(func.sum(NotaFiscal.valor_total)).filter(
            NotaFiscal.status_processamento == 'validado'
        ).scalar() or 0

        # Valor total pendente de validação
        total_valor_pendente = self.db.query(func.sum(NotaFiscal.valor_total)).filter(
            NotaFiscal.status_processamento == 'processado'
        ).scalar() or 0

        # Contratos com NFs
        contratos_com_nfs = self.db.query(NotaFiscal.contrato_id).filter(
            NotaFiscal.contrato_id.isnot(None)
        ).distinct().count()

        # NFs não classificadas por contrato
        nfs_sem_contrato = self.db.query(NotaFiscal).filter(
            NotaFiscal.contrato_id.is_(None)
        ).count()

        # Fornecedores únicos
        fornecedores_unicos = self.db.query(NotaFiscal.cnpj_fornecedor).distinct().count()

        # Valor médio por NF
        valor_medio_nf = float(total_valor_validado) / nfs_validadas if nfs_validadas > 0 else 0

        # Estatísticas por centro de custo
        centros_custo_stats = self.db.query(
            CostCenter.nome,
            func.count(NotaFiscalItem.id).label('total_itens'),
            func.sum(NotaFiscalItem.valor_total).label('valor_total')
        ).join(
            NotaFiscalItem, CostCenter.id == NotaFiscalItem.centro_custo_id
        ).join(
            NotaFiscal, NotaFiscalItem.nota_fiscal_id == NotaFiscal.id
        ).filter(
            NotaFiscal.status_processamento == 'validado'
        ).group_by(CostCenter.nome).all()

        centros_custo_data = []
        for nome, total_itens, valor_total in centros_custo_stats:
            centros_custo_data.append({
                "nome": nome,
                "total_itens": total_itens,
                "valor_total": float(valor_total or 0)
            })

        return {
            "resumo_nfs": {
                "total": total_nfs,
                "validadas": nfs_validadas,
                "pendentes": nfs_pendentes,
                "com_erro": nfs_erro,
                "taxa_validacao": (nfs_validadas / total_nfs * 100) if total_nfs > 0 else 0
            },
            "valores": {
                "total_validado": float(total_valor_validado),
                "total_pendente": float(total_valor_pendente),
                "valor_medio_nf": valor_medio_nf
            },
            "contratos": {
                "contratos_com_nfs": contratos_com_nfs,
                "nfs_sem_contrato": nfs_sem_contrato
            },
            "fornecedores": {
                "fornecedores_unicos": fornecedores_unicos
            },
            "centros_custo": centros_custo_data,
            "generated_at": datetime.now().isoformat()
        }

    def get_contracts_summary_with_nfs(self) -> List[Dict[str, Any]]:
        """Retorna sumário de todos os contratos com informações das NFs"""

        contracts = self.db.query(Contract).all()
        contracts_summary = []

        for contract in contracts:
            # Buscar NFs do contrato
            nfs_count = self.db.query(NotaFiscal).filter(
                NotaFiscal.contrato_id == contract.id
            ).count()

            nfs_validadas = self.db.query(NotaFiscal).filter(
                and_(
                    NotaFiscal.contrato_id == contract.id,
                    NotaFiscal.status_processamento == 'validado'
                )
            ).count()

            # Calcular valor realizado
            valor_realizado = self.calculate_contract_realized_value(contract.id)

            contracts_summary.append({
                "id": contract.id,
                "numero_contrato": contract.numero_contrato,
                "nome_projeto": contract.nome_projeto,
                "cliente": contract.cliente,
                "valor_original": float(contract.valor_original),
                "valor_realizado": float(valor_realizado),
                "percentual_realizado": (float(valor_realizado) / float(contract.valor_original) * 100) if contract.valor_original > 0 else 0,
                "saldo_restante": float(contract.valor_original) - float(valor_realizado),
                "status": contract.status,
                "total_nfs": nfs_count,
                "nfs_validadas": nfs_validadas,
                "nfs_pendentes": nfs_count - nfs_validadas,
                "data_inicio": contract.data_inicio.strftime("%Y-%m-%d") if contract.data_inicio else None,
                "data_fim_prevista": contract.data_fim_prevista.strftime("%Y-%m-%d") if contract.data_fim_prevista else None
            })

        return contracts_summary