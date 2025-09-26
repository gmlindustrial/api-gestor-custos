import pandas as pd
import xml.etree.ElementTree as ET
import json
import asyncio
from typing import List, Dict, Any, Optional, Union
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException, status
import os
import tempfile
import aiofiles
import openpyxl
from app.models.contracts import Contract, BudgetItem, ValorPrevisto
from app.models.purchases import Invoice, InvoiceItem, PurchaseOrder
from app.models.cost_centers import CostCenter
from app.schemas.contracts import BudgetItemCreate


class DataImportService:
    def __init__(self, db: Session):
        self.db = db
        self.temp_dir = tempfile.gettempdir()
        
        # Mapeamento de colunas comuns
        self.budget_column_mapping = {
            'codigo': 'codigo_item',
            'código': 'codigo_item',
            'item': 'codigo_item',
            'descricao': 'descricao',
            'descrição': 'descricao',
            'centro_custo': 'centro_custo',
            'centro de custo': 'centro_custo',
            'cc': 'centro_custo',
            'unidade': 'unidade',
            'un': 'unidade',
            'quantidade': 'quantidade_prevista',
            'qtd': 'quantidade_prevista',
            'peso': 'peso_previsto',
            'valor_unitario': 'valor_unitario_previsto',
            'valor unitário': 'valor_unitario_previsto',
            'preco_unitario': 'valor_unitario_previsto',
            'preço unitário': 'valor_unitario_previsto',
            'valor_total': 'valor_total_previsto',
            'valor total': 'valor_total_previsto',
            'total': 'valor_total_previsto'
        }
        
        self.invoice_column_mapping = {
            'descricao': 'descricao',
            'descrição': 'descricao',
            'produto': 'descricao',
            'item': 'descricao',
            'centro_custo': 'centro_custo',
            'centro de custo': 'centro_custo',
            'cc': 'centro_custo',
            'unidade': 'unidade',
            'un': 'unidade',
            'quantidade': 'quantidade',
            'qtd': 'quantidade',
            'peso': 'peso',
            'valor_unitario': 'valor_unitario',
            'valor unitário': 'valor_unitario',
            'preco_unitario': 'valor_unitario',
            'preço unitário': 'valor_unitario',
            'valor_total': 'valor_total',
            'valor total': 'valor_total',
            'total': 'valor_total'
        }

    async def import_budget_from_excel(
        self,
        file: UploadFile,
        contract_id: int = None,
        sheet_name: str = "QQP_Cliente",
        skip_rows: int = 0
    ) -> Dict[str, Any]:
        """
        Importa orçamento previsto de planilha Excel (QQP Cliente)
        Retorna tanto os itens quanto o valor total do contrato
        """
        if not file.filename.endswith(('.xlsx', '.xls', '.xlsm')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Arquivo deve ser Excel (.xlsx, .xls ou .xlsm)"
            )

        # Salvar arquivo temporariamente
        temp_path = os.path.join(self.temp_dir, f"budget_{contract_id or 'new'}_{file.filename}")

        async with aiofiles.open(temp_path, 'wb') as temp_file:
            content = await file.read()
            await temp_file.write(content)

        try:
            # Se contract_id for fornecido, verificar se existe
            if contract_id:
                contract = self.db.query(Contract).filter(Contract.id == contract_id).first()
                if not contract:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Contrato não encontrado"
                    )

            # Ler planilha QQP_Cliente sem header para processar estrutura customizada
            df = pd.read_excel(temp_path, sheet_name=sheet_name, header=None)

            # Extrair valor total do contrato (linha 40, coluna 4)
            valor_total_contrato = None
            if df.shape[0] > 40 and df.shape[1] > 4:
                valor_total = df.iloc[40, 4]
                if pd.notna(valor_total) and isinstance(valor_total, (int, float)):
                    valor_total_contrato = Decimal(str(valor_total))

            # Processar tabela de serviços detalhados (linhas 11-21)
            valores_previstos = []
            errors = []

            for i in range(11, min(22, df.shape[0])):
                try:
                    row = df.iloc[i]

                    # Verificar se a linha tem dados válidos (item, serviço e preço total)
                    if pd.notna(row[2]) and pd.notna(row[3]) and pd.notna(row[12]):
                        # Função auxiliar para converter para Decimal
                        def to_decimal_safe(value):
                            if pd.notna(value) and value != '':
                                try:
                                    return Decimal(str(value))
                                except:
                                    return None
                            return None

                        item_data = {
                            'item': str(row[2]),  # Coluna 2: Código do item
                            'servicos': str(row[3]),  # Coluna 3: Descrição do serviço
                            'unidade': str(row[4]) if pd.notna(row[4]) else None,  # Coluna 4: Unidade
                            'qtd_mensal': to_decimal_safe(row[5]),  # Coluna 6: QTD Mensal (row[5] = coluna 6)
                            'duracao_meses': to_decimal_safe(row[6]),  # Coluna 7: Duração Meses (row[6] = coluna 7)
                            'preco_total': Decimal(str(row[12])),  # Coluna 12: Preço Total
                            'observacao': str(row[13]) if pd.notna(row[13]) else None  # Coluna 13: Observação
                        }

                        # Se contract_id fornecido, criar item no banco
                        if contract_id:
                            valor_previsto = ValorPrevisto(
                                contract_id=contract_id,
                                **{k: v for k, v in item_data.items() if v is not None}
                            )
                            self.db.add(valor_previsto)

                        valores_previstos.append(item_data)

                except Exception as e:
                    errors.append(f"Linha {i + 1}: {str(e)}")

            # Commit apenas se contract_id foi fornecido
            if contract_id and valores_previstos:
                self.db.commit()
            
            return {
                'success': True,
                'imported_items': len(valores_previstos),
                'errors': errors,
                'items_total': sum(item['preco_total'] for item in valores_previstos if item['preco_total']),
                'contract_total_value': valor_total_contrato,  # Valor total do contrato
                'valores_previstos': valores_previstos  # Incluir os itens para uso na criação
            }
            
        finally:
            # Limpar arquivo temporário
            if os.path.exists(temp_path):
                os.remove(temp_path)

    async def import_invoice_from_xml(self, file: UploadFile, purchase_order_id: int) -> Dict[str, Any]:
        """
        Importa nota fiscal de arquivo XML
        """
        if not file.filename.endswith('.xml'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Arquivo deve ser XML"
            )

        # Verificar se a ordem de compra existe
        purchase_order = self.db.query(PurchaseOrder).filter(PurchaseOrder.id == purchase_order_id).first()
        if not purchase_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ordem de compra não encontrada"
            )

        content = await file.read()
        
        try:
            # Parse XML
            root = ET.fromstring(content)
            
            # Extrair dados da NF-e (padrão brasileiro)
            nfe_data = self._extract_nfe_data(root)
            
            # Criar invoice
            invoice = Invoice(
                purchase_order_id=purchase_order_id,
                numero_nf=nfe_data['numero'],
                valor_total=nfe_data['valor_total'],
                data_emissao=nfe_data['data_emissao'],
                observacoes=f"Importado de XML: {file.filename}"
            )
            
            self.db.add(invoice)
            self.db.commit()
            self.db.refresh(invoice)
            
            # Criar itens da invoice
            for item_data in nfe_data['itens']:
                centro_custo = self._classify_cost_center(item_data['descricao'])
                
                invoice_item = InvoiceItem(
                    invoice_id=invoice.id,
                    descricao=item_data['descricao'],
                    centro_custo=centro_custo,
                    unidade=item_data.get('unidade'),
                    quantidade=item_data.get('quantidade'),
                    valor_unitario=item_data.get('valor_unitario'),
                    valor_total=item_data['valor_total']
                )
                
                self.db.add(invoice_item)
            
            self.db.commit()
            
            return {
                'success': True,
                'invoice_id': invoice.id,
                'numero_nf': invoice.numero_nf,
                'valor_total': invoice.valor_total,
                'items_imported': len(nfe_data['itens'])
            }
            
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Erro ao processar XML: {str(e)}"
            )

    async def import_invoice_from_excel(
        self, 
        file: UploadFile, 
        purchase_order_id: int,
        sheet_name: str = None,
        skip_rows: int = 0
    ) -> Dict[str, Any]:
        """
        Importa itens de nota fiscal de planilha Excel
        """
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Arquivo deve ser Excel (.xlsx ou .xls)"
            )

        # Verificar se a ordem de compra existe
        purchase_order = self.db.query(PurchaseOrder).filter(PurchaseOrder.id == purchase_order_id).first()
        if not purchase_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ordem de compra não encontrada"
            )

        # Salvar arquivo temporariamente
        temp_path = os.path.join(self.temp_dir, f"invoice_{purchase_order_id}_{file.filename}")
        
        async with aiofiles.open(temp_path, 'wb') as temp_file:
            content = await file.read()
            await temp_file.write(content)

        try:
            # Ler planilha
            if sheet_name:
                df = pd.read_excel(temp_path, sheet_name=sheet_name, skiprows=skip_rows)
            else:
                df = pd.read_excel(temp_path, skiprows=skip_rows)
            
            # Normalizar nomes das colunas
            df.columns = df.columns.str.lower().str.strip()
            
            # Mapear colunas
            df_mapped = self._map_columns(df, self.invoice_column_mapping)
            
            # Validar colunas obrigatórias
            required_columns = ['descricao', 'valor_total']
            missing_columns = [col for col in required_columns if col not in df_mapped.columns]
            
            if missing_columns:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Colunas obrigatórias ausentes: {missing_columns}"
                )

            # Criar invoice se não existir
            invoice = Invoice(
                purchase_order_id=purchase_order_id,
                numero_nf=f"IMPORT_{purchase_order_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                valor_total=df_mapped['valor_total'].sum(),
                data_emissao=datetime.now(),
                observacoes=f"Importado de planilha: {file.filename}"
            )
            
            self.db.add(invoice)
            self.db.commit()
            self.db.refresh(invoice)
            
            # Processar itens
            items_imported = 0
            errors = []
            
            for index, row in df_mapped.iterrows():
                try:
                    centro_custo = self._classify_cost_center(row['descricao'])
                    
                    invoice_item = InvoiceItem(
                        invoice_id=invoice.id,
                        descricao=str(row['descricao']),
                        centro_custo=row.get('centro_custo', centro_custo),
                        unidade=row.get('unidade'),
                        quantidade=self._to_decimal(row.get('quantidade')),
                        peso=self._to_decimal(row.get('peso')),
                        valor_unitario=self._to_decimal(row.get('valor_unitario')),
                        valor_total=self._to_decimal(row['valor_total'])
                    )
                    
                    self.db.add(invoice_item)
                    items_imported += 1
                    
                except Exception as e:
                    errors.append(f"Linha {index + 1}: {str(e)}")
            
            self.db.commit()
            
            return {
                'success': True,
                'invoice_id': invoice.id,
                'items_imported': items_imported,
                'errors': errors,
                'total_value': float(invoice.valor_total)
            }
            
        finally:
            # Limpar arquivo temporário
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def _map_columns(self, df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
        """
        Mapeia colunas do DataFrame usando o mapeamento fornecido
        """
        column_map = {}
        for col in df.columns:
            clean_col = col.lower().strip()
            if clean_col in mapping:
                column_map[col] = mapping[clean_col]
        
        return df.rename(columns=column_map)

    def _classify_cost_center(self, description: str) -> str:
        """
        Classifica automaticamente o centro de custo baseado na descrição
        """
        description_lower = description.lower()
        
        # Regras de classificação automática
        if any(word in description_lower for word in ['aço', 'ferro', 'metallic', 'metal', 'vergalhão']):
            return 'MATERIA_PRIMA'
        elif any(word in description_lower for word in ['mão de obra', 'mao de obra', 'trabalho', 'servico']):
            return 'MAO_DE_OBRA'
        elif any(word in description_lower for word in ['transporte', 'frete', 'entrega']):
            return 'MOBILIZACAO'
        elif any(word in description_lower for word in ['equipamento', 'maquina', 'ferramenta']):
            return 'EQUIPAMENTOS'
        else:
            return 'OUTROS'

    def _to_decimal(self, value) -> Optional[Decimal]:
        """
        Converte valor para Decimal, tratando diferentes formatos
        """
        if pd.isna(value) or value is None:
            return None
        
        try:
            # Remover símbolos de moeda e espaços
            if isinstance(value, str):
                value = value.replace('R$', '').replace('$', '').replace(',', '.').strip()
            
            return Decimal(str(value))
        except:
            return None

    def _extract_nfe_data(self, root: ET.Element) -> Dict[str, Any]:
        """
        Extrai dados de uma NF-e XML (padrão brasileiro)
        """
        # Namespaces comuns da NF-e
        ns = {
            'nfe': 'http://www.portalfiscal.inf.br/nfe'
        }
        
        try:
            # Buscar dados principais da NF
            inf_nfe = root.find('.//nfe:infNFe', ns)
            ide = inf_nfe.find('nfe:ide', ns)
            total = inf_nfe.find('.//nfe:total/nfe:ICMSTot', ns)
            
            numero = ide.find('nfe:nNF', ns).text
            data_emissao = datetime.strptime(ide.find('nfe:dhEmi', ns).text[:10], '%Y-%m-%d')
            valor_total = Decimal(total.find('nfe:vNF', ns).text)
            
            # Extrair itens
            itens = []
            for det in inf_nfe.findall('nfe:det', ns):
                prod = det.find('nfe:prod', ns)
                
                item = {
                    'descricao': prod.find('nfe:xProd', ns).text,
                    'unidade': prod.find('nfe:uCom', ns).text,
                    'quantidade': Decimal(prod.find('nfe:qCom', ns).text),
                    'valor_unitario': Decimal(prod.find('nfe:vUnCom', ns).text),
                    'valor_total': Decimal(prod.find('nfe:vProd', ns).text)
                }
                
                itens.append(item)
            
            return {
                'numero': numero,
                'data_emissao': data_emissao,
                'valor_total': valor_total,
                'itens': itens
            }
            
        except Exception as e:
            raise ValueError(f"Erro ao extrair dados da NF-e: {str(e)}")

    async def validate_file_format(self, file: UploadFile) -> Dict[str, Any]:
        """
        Valida formato do arquivo e retorna informações básicas
        """
        file_info = {
            'filename': file.filename,
            'size': 0,
            'type': None,
            'valid': False,
            'sheets': []
        }
        
        # Calcular tamanho
        content = await file.read()
        file_info['size'] = len(content)
        
        # Resetar ponteiro do arquivo
        await file.seek(0)
        
        if file.filename.endswith('.xlsx') or file.filename.endswith('.xls'):
            file_info['type'] = 'excel'
            file_info['valid'] = True
            
            # Listar planilhas (sheets)
            try:
                temp_path = os.path.join(self.temp_dir, f"validate_{file.filename}")
                async with aiofiles.open(temp_path, 'wb') as temp_file:
                    await temp_file.write(content)
                
                workbook = openpyxl.load_workbook(temp_path)
                file_info['sheets'] = workbook.sheetnames
                
                os.remove(temp_path)
            except:
                pass
                
        elif file.filename.endswith('.xml'):
            file_info['type'] = 'xml'
            file_info['valid'] = True
            
        elif file.filename.endswith('.csv'):
            file_info['type'] = 'csv'
            file_info['valid'] = True
        
        return file_info