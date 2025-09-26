"""Serviço de relatórios simplificado sem dependências pesadas"""

from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from decimal import Decimal
import json
from io import BytesIO

from app.models.contracts import Contract
from app.models.purchases import PurchaseOrder, Invoice
from app.models.users import User


class SimpleReportsService:
    def __init__(self, db: Session):
        self.db = db

    def generate_analytical_report(
        self,
        contract_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Gera relatório analítico detalhado para uso interno"""

        query = self.db.query(Contract)
        if contract_id:
            query = query.filter(Contract.id == contract_id)

        contracts = query.all()

        report_data = {
            "title": "Relatório Analítico - Custos de Obras",
            "generated_at": datetime.now().isoformat(),
            "period": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None
            },
            "contracts": []
        }

        for contract in contracts:
            contract_data = {
                "id": contract.id,
                "name": contract.nome_contrato,
                "client_name": contract.cliente,
                "contract_value": float(contract.valor_contrato or 0),
                "start_date": contract.data_inicio.isoformat() if contract.data_inicio else None,
                "end_date": contract.data_fim.isoformat() if contract.data_fim else None,
                "status": contract.status,
                "purchases": [],
                "invoices": [],
                "metrics": self._calculate_contract_metrics(contract.id)
            }

            # Buscar compras do contrato
            purchases = self.db.query(PurchaseOrder).filter(
                PurchaseOrder.contract_id == contract.id
            ).all()

            for purchase in purchases:
                purchase_data = {
                    "id": purchase.id,
                    "numero_oc": purchase.numero_oc,
                    "supplier": purchase.supplier.nome if purchase.supplier else "N/A",
                    "total_value": float(purchase.valor_total),
                    "emission_date": purchase.data_emissao.isoformat(),
                    "status": purchase.status
                }
                contract_data["purchases"].append(purchase_data)

                # Buscar notas fiscais da compra
                invoices = self.db.query(Invoice).filter(
                    Invoice.purchase_order_id == purchase.id
                ).all()

                for invoice in invoices:
                    invoice_data = {
                        "id": invoice.id,
                        "numero_nf": invoice.numero_nf,
                        "total_value": float(invoice.valor_total),
                        "emission_date": invoice.data_emissao.isoformat(),
                        "due_date": invoice.data_vencimento.isoformat() if invoice.data_vencimento else None,
                        "payment_date": invoice.data_pagamento.isoformat() if invoice.data_pagamento else None
                    }
                    contract_data["invoices"].append(invoice_data)

            report_data["contracts"].append(contract_data)

        return report_data

    def generate_synthetic_report(
        self,
        contract_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Gera relatório sintético para clientes"""

        query = self.db.query(Contract)
        if contract_id:
            query = query.filter(Contract.id == contract_id)

        contracts = query.all()

        report_data = {
            "title": "Relatório de Conta-Corrente",
            "generated_at": datetime.now().isoformat(),
            "contracts": []
        }

        for contract in contracts:
            metrics = self._calculate_contract_metrics(contract.id)
            contract_data = {
                "contract_name": contract.nome_contrato,
                "client_name": contract.cliente,
                "contract_value": float(contract.valor_contrato or 0),
                "realized_value": metrics.get("valor_realizado", 0),
                "contract_balance": metrics.get("saldo_contrato", 0),
                "realization_percentage": metrics.get("percentual_realizado", 0),
                "savings_obtained": metrics.get("economia_obtida", 0),
                "savings_percentage": metrics.get("percentual_economia", 0)
            }
            report_data["contracts"].append(contract_data)

        return report_data

    def _calculate_contract_metrics(self, contract_id: int) -> Dict[str, float]:
        """Calcula métricas básicas do contrato"""

        contract = self.db.query(Contract).filter(Contract.id == contract_id).first()
        if not contract:
            return {}

        # Somar valor total das compras
        total_purchases = self.db.query(PurchaseOrder).filter(
            PurchaseOrder.contract_id == contract_id
        ).all()

        valor_realizado = sum(float(po.valor_total) for po in total_purchases)
        valor_contrato = float(contract.valor_contrato or 0)
        saldo_contrato = valor_contrato - valor_realizado

        percentual_realizado = (valor_realizado / valor_contrato * 100) if valor_contrato > 0 else 0
        economia_obtida = saldo_contrato if saldo_contrato > 0 else 0
        percentual_economia = (economia_obtida / valor_contrato * 100) if valor_contrato > 0 else 0

        return {
            "valor_realizado": valor_realizado,
            "saldo_contrato": saldo_contrato,
            "percentual_realizado": percentual_realizado,
            "economia_obtida": economia_obtida,
            "percentual_economia": percentual_economia
        }

    def export_to_json(self, report_data: Dict[str, Any]) -> str:
        """Exporta relatório em formato JSON"""
        return json.dumps(report_data, indent=2, ensure_ascii=False)

    def generate_pdf_report(self, report_data: Dict[str, Any]) -> BytesIO:
        """Gera relatório em PDF usando ReportLab"""
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            alignment=1  # Center alignment
        )

        story = []

        # Título
        title = Paragraph(report_data.get("title", "Relatório"), title_style)
        story.append(title)
        story.append(Spacer(1, 12))

        # Data de geração
        generated_at = Paragraph(
            f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            styles['Normal']
        )
        story.append(generated_at)
        story.append(Spacer(1, 12))

        # Conteúdo dos contratos
        for contract in report_data.get("contracts", []):
            # Nome do contrato
            contract_title = Paragraph(
                f"<b>{contract.get('contract_name', contract.get('name', 'N/A'))}</b>",
                styles['Heading2']
            )
            story.append(contract_title)

            # Tabela com dados do contrato
            data = [
                ['Cliente:', contract.get('client_name', 'N/A')],
                ['Valor do Contrato:', f"R$ {contract.get('contract_value', 0):,.2f}"],
            ]

            if 'realized_value' in contract:
                data.extend([
                    ['Valor Realizado:', f"R$ {contract.get('realized_value', 0):,.2f}"],
                    ['Saldo do Contrato:', f"R$ {contract.get('contract_balance', 0):,.2f}"],
                    ['Percentual Realizado:', f"{contract.get('realization_percentage', 0):.1f}%"],
                    ['Economia Obtida:', f"R$ {contract.get('savings_obtained', 0):,.2f}"],
                ])

            table = Table(data, colWidths=[2*inch, 3*inch])
            table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))

            story.append(table)
            story.append(Spacer(1, 12))

        doc.build(story)
        buffer.seek(0)
        return buffer