from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime
import uuid
import os
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
import pandas as pd
from app.models.contracts import Contract, BudgetItem
from app.models.purchases import PurchaseOrder, PurchaseOrderItem, Invoice, InvoiceItem, Supplier
from app.schemas.reports import (
    ReportFilter, ReportType, ReportFormat, ReportRequest,
    AnalyticalReport, AnalyticalReportItem, 
    ContractBalanceReport, SyntheticReportItem
)


class ReportsService:
    def __init__(self, db: Session):
        self.db = db
        self.reports_dir = "reports"
        os.makedirs(self.reports_dir, exist_ok=True)

    def generate_report(self, request: ReportRequest) -> Dict[str, Any]:
        if request.report_type == ReportType.ANALITICO:
            return self._generate_analytical_report(request)
        elif request.report_type == ReportType.SINTETICO:
            return self._generate_synthetic_report(request)
        elif request.report_type == ReportType.CONTA_CORRENTE:
            return self._generate_balance_report(request)
        else:
            raise ValueError("Tipo de relatório não suportado")

    def _generate_analytical_report(self, request: ReportRequest) -> Dict[str, Any]:
        filters = request.filters
        
        # Query base para itens de nota fiscal
        query = self.db.query(
            InvoiceItem,
            Invoice,
            PurchaseOrder,
            Contract,
            Supplier
        ).join(
            Invoice, InvoiceItem.invoice_id == Invoice.id
        ).join(
            PurchaseOrder, Invoice.purchase_order_id == PurchaseOrder.id
        ).join(
            Contract, PurchaseOrder.contract_id == Contract.id
        ).join(
            Supplier, PurchaseOrder.supplier_id == Supplier.id
        )

        # Aplicar filtros
        if filters.contract_id:
            query = query.filter(Contract.id == filters.contract_id)
        
        if filters.cliente:
            query = query.filter(Contract.cliente.ilike(f"%{filters.cliente}%"))
        
        if filters.data_inicio:
            query = query.filter(Invoice.data_emissao >= filters.data_inicio)
        
        if filters.data_fim:
            query = query.filter(Invoice.data_emissao <= filters.data_fim)
        
        if filters.centro_custo:
            query = query.filter(InvoiceItem.centro_custo.ilike(f"%{filters.centro_custo}%"))
        
        if filters.fornecedor:
            query = query.filter(Supplier.nome.ilike(f"%{filters.fornecedor}%"))

        results = query.all()

        # Processar resultados
        items = []
        total_geral = Decimal('0')
        
        for invoice_item, invoice, po, contract, supplier in results:
            item = AnalyticalReportItem(
                id=invoice_item.id,
                descricao=invoice_item.descricao,
                fornecedor=supplier.nome,
                centro_custo=invoice_item.centro_custo,
                numero_oc=po.numero_oc,
                numero_nf=invoice.numero_nf,
                data_emissao=invoice.data_emissao,
                data_entrega=po.data_entrega_real,
                quantidade=invoice_item.quantidade,
                unidade=invoice_item.unidade,
                peso=invoice_item.peso,
                valor_unitario=invoice_item.valor_unitario,
                valor_total=invoice_item.valor_total,
                observacoes=invoice.observacoes
            )
            items.append(item)
            total_geral += invoice_item.valor_total

        # Buscar informações do contrato
        contract_info = None
        if filters.contract_id:
            contract_info = self.db.query(Contract).filter(Contract.id == filters.contract_id).first()

        report_data = AnalyticalReport(
            contract_id=filters.contract_id or 0,
            numero_contrato=contract_info.numero_contrato if contract_info else "Todos",
            nome_projeto=contract_info.nome_projeto if contract_info else "Relatório Geral",
            periodo_inicio=filters.data_inicio,
            periodo_fim=filters.data_fim,
            total_geral=total_geral,
            itens=items
        )

        # Gerar arquivo se necessário
        file_url = None
        if request.format == ReportFormat.PDF:
            file_url = self._generate_pdf_analytical(report_data)
        elif request.format == ReportFormat.EXCEL:
            file_url = self._generate_excel_analytical(report_data)

        return {
            "report_id": str(uuid.uuid4()),
            "report_type": request.report_type,
            "format": request.format,
            "generated_at": datetime.utcnow(),
            "file_url": file_url,
            "data": report_data.dict() if request.format == ReportFormat.JSON else None
        }

    def _generate_balance_report(self, request: ReportRequest) -> Dict[str, Any]:
        filters = request.filters
        
        if not filters.contract_id:
            raise ValueError("contract_id é obrigatório para relatório de conta-corrente")

        # Buscar contrato
        contract = self.db.query(Contract).filter(Contract.id == filters.contract_id).first()
        if not contract:
            raise ValueError("Contrato não encontrado")

        # Buscar itens sintéticos (notas fiscais)
        query = self.db.query(
            Invoice.data_emissao,
            PurchaseOrder.numero_oc,
            Invoice.numero_nf,
            Supplier.nome,
            Invoice.valor_total
        ).join(
            PurchaseOrder, Invoice.purchase_order_id == PurchaseOrder.id
        ).join(
            Supplier, PurchaseOrder.supplier_id == Supplier.id
        ).filter(
            PurchaseOrder.contract_id == filters.contract_id
        )

        if filters.data_inicio:
            query = query.filter(Invoice.data_emissao >= filters.data_inicio)
        
        if filters.data_fim:
            query = query.filter(Invoice.data_emissao <= filters.data_fim)

        results = query.all()

        # Processar itens sintéticos
        itens_sinteticos = []
        valor_realizado = Decimal('0')
        
        for data, numero_oc, numero_nf, fornecedor, valor in results:
            item = SyntheticReportItem(
                data=data,
                numero_oc=numero_oc,
                numero_nf=numero_nf,
                fornecedor=fornecedor,
                valor_total=valor
            )
            itens_sinteticos.append(item)
            valor_realizado += valor

        # Calcular saldo
        saldo_contrato = contract.valor_original - valor_realizado
        percentual_realizado = (valor_realizado / contract.valor_original * 100) if contract.valor_original > 0 else Decimal('0')

        report_data = ContractBalanceReport(
            contract_id=contract.id,
            numero_contrato=contract.numero_contrato,
            nome_projeto=contract.nome_projeto,
            cliente=contract.cliente,
            valor_original=contract.valor_original,
            valor_realizado=valor_realizado,
            saldo_contrato=saldo_contrato,
            percentual_realizado=percentual_realizado,
            itens_sinteticos=itens_sinteticos
        )

        # Gerar arquivo se necessário
        file_url = None
        if request.format == ReportFormat.PDF:
            file_url = self._generate_pdf_balance(report_data)
        elif request.format == ReportFormat.EXCEL:
            file_url = self._generate_excel_balance(report_data)

        return {
            "report_id": str(uuid.uuid4()),
            "report_type": request.report_type,
            "format": request.format,
            "generated_at": datetime.utcnow(),
            "file_url": file_url,
            "data": report_data.dict() if request.format == ReportFormat.JSON else None
        }

    def _generate_synthetic_report(self, request: ReportRequest) -> Dict[str, Any]:
        # Para o relatório sintético, usamos a mesma lógica do conta-corrente
        # mas sem mostrar o saldo (apenas para clientes)
        return self._generate_balance_report(request)

    def _generate_pdf_analytical(self, report_data: AnalyticalReport) -> str:
        filename = f"relatorio_analitico_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(self.reports_dir, filename)
        
        doc = SimpleDocTemplate(filepath, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        # Título
        title = Paragraph(f"Relatório Analítico - {report_data.nome_projeto}", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 12))

        # Informações gerais
        info = f"Contrato: {report_data.numero_contrato}<br/>Total Geral: R$ {report_data.total_geral:,.2f}"
        info_para = Paragraph(info, styles['Normal'])
        story.append(info_para)
        story.append(Spacer(1, 12))

        # Tabela de itens
        headers = ['Descrição', 'Fornecedor', 'Centro Custo', 'Nº NF', 'Quantidade', 'Valor Total']
        data = [headers]
        
        for item in report_data.itens:
            row = [
                item.descricao[:30] + "..." if len(item.descricao) > 30 else item.descricao,
                item.fornecedor,
                item.centro_custo,
                item.numero_nf or "",
                str(item.quantidade or ""),
                f"R$ {item.valor_total:,.2f}"
            ]
            data.append(row)

        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        story.append(table)
        doc.build(story)
        
        return f"/reports/{filename}"

    def _generate_excel_analytical(self, report_data: AnalyticalReport) -> str:
        filename = f"relatorio_analitico_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = os.path.join(self.reports_dir, filename)
        
        # Converter dados para DataFrame
        data = []
        for item in report_data.itens:
            data.append({
                'Descrição': item.descricao,
                'Fornecedor': item.fornecedor,
                'Centro de Custo': item.centro_custo,
                'Nº OC': item.numero_oc,
                'Nº NF': item.numero_nf,
                'Data Emissão': item.data_emissao,
                'Quantidade': item.quantidade,
                'Unidade': item.unidade,
                'Peso': item.peso,
                'Valor Unitário': item.valor_unitario,
                'Valor Total': item.valor_total,
                'Observações': item.observacoes
            })

        df = pd.DataFrame(data)
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Relatório Analítico', index=False)
            
            # Adicionar informações do cabeçalho
            workbook = writer.book
            worksheet = writer.sheets['Relatório Analítico']
            
            worksheet.insert_rows(1, 3)
            worksheet['A1'] = f'Relatório Analítico - {report_data.nome_projeto}'
            worksheet['A2'] = f'Contrato: {report_data.numero_contrato}'
            worksheet['A3'] = f'Total Geral: R$ {report_data.total_geral:,.2f}'

        return f"/reports/{filename}"

    def _generate_pdf_balance(self, report_data: ContractBalanceReport) -> str:
        filename = f"conta_corrente_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(self.reports_dir, filename)
        
        doc = SimpleDocTemplate(filepath, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        # Título
        title = Paragraph(f"Conta-Corrente do Contrato", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 12))

        # Informações do contrato
        info = f"""
        Contrato: {report_data.numero_contrato}<br/>
        Projeto: {report_data.nome_projeto}<br/>
        Cliente: {report_data.cliente}<br/>
        Valor Original: R$ {report_data.valor_original:,.2f}<br/>
        Valor Realizado: R$ {report_data.valor_realizado:,.2f}<br/>
        Saldo: R$ {report_data.saldo_contrato:,.2f}<br/>
        % Realizado: {report_data.percentual_realizado:.1f}%
        """
        info_para = Paragraph(info, styles['Normal'])
        story.append(info_para)
        story.append(Spacer(1, 20))

        # Tabela de movimentações
        headers = ['Data', 'Nº OC', 'Nº NF', 'Fornecedor', 'Valor']
        data = [headers]
        
        for item in report_data.itens_sinteticos:
            row = [
                item.data.strftime('%d/%m/%Y'),
                item.numero_oc,
                item.numero_nf,
                item.fornecedor,
                f"R$ {item.valor_total:,.2f}"
            ]
            data.append(row)

        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        story.append(table)
        doc.build(story)
        
        return f"/reports/{filename}"

    def _generate_excel_balance(self, report_data: ContractBalanceReport) -> str:
        filename = f"conta_corrente_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = os.path.join(self.reports_dir, filename)
        
        # Converter dados para DataFrame
        data = []
        for item in report_data.itens_sinteticos:
            data.append({
                'Data': item.data,
                'Nº OC': item.numero_oc,
                'Nº NF': item.numero_nf,
                'Fornecedor': item.fornecedor,
                'Valor Total': item.valor_total
            })

        df = pd.DataFrame(data)
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Conta-Corrente', index=False)
            
            # Adicionar informações do cabeçalho
            workbook = writer.book
            worksheet = writer.sheets['Conta-Corrente']
            
            worksheet.insert_rows(1, 8)
            worksheet['A1'] = f'Conta-Corrente do Contrato'
            worksheet['A2'] = f'Contrato: {report_data.numero_contrato}'
            worksheet['A3'] = f'Projeto: {report_data.nome_projeto}'
            worksheet['A4'] = f'Cliente: {report_data.cliente}'
            worksheet['A5'] = f'Valor Original: R$ {report_data.valor_original:,.2f}'
            worksheet['A6'] = f'Valor Realizado: R$ {report_data.valor_realizado:,.2f}'
            worksheet['A7'] = f'Saldo: R$ {report_data.saldo_contrato:,.2f}'
            worksheet['A8'] = f'% Realizado: {report_data.percentual_realizado:.1f}%'

        return f"/reports/{filename}"