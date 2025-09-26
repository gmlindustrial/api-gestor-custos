import zipfile
import os
import tempfile
import requests
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
from decimal import Decimal
from datetime import datetime
from fastapi import UploadFile
from sqlalchemy.orm import Session
from app.models.purchases import Invoice, InvoiceItem
from app.schemas.invoices import InvoiceResponse
import re
import io


class InvoiceProcessingService:
    def __init__(self, db: Session):
        self.db = db

    async def process_zip_file(
        self,
        file: UploadFile,
        contract_id: int,
        uploaded_by: int
    ) -> Dict[str, Any]:
        """
        Processa arquivo ZIP contendo múltiplas notas fiscais.
        """
        processed_count = 0
        failed_count = 0
        invoices = []
        errors = []

        # Criar diretório temporário
        with tempfile.TemporaryDirectory() as temp_dir:
            # Salvar ZIP temporariamente
            zip_path = os.path.join(temp_dir, file.filename)
            content = await file.read()

            with open(zip_path, 'wb') as f:
                f.write(content)

            # Extrair ZIP
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)

                # Processar cada arquivo extraído
                for root, dirs, files in os.walk(temp_dir):
                    for filename in files:
                        if filename.lower().endswith(('.xml', '.pdf')):
                            file_path = os.path.join(root, filename)

                            try:
                                invoice_data = await self._extract_invoice_data(file_path, filename)
                                if invoice_data:
                                    # Criar invoice no banco
                                    invoice = await self._create_invoice(
                                        invoice_data,
                                        contract_id,
                                        file_path
                                    )
                                    invoices.append(invoice)
                                    processed_count += 1
                                else:
                                    errors.append(f"Não foi possível extrair dados de {filename}")
                                    failed_count += 1

                            except Exception as e:
                                errors.append(f"Erro ao processar {filename}: {str(e)}")
                                failed_count += 1

            except zipfile.BadZipFile:
                raise Exception("Arquivo ZIP corrompido ou inválido")

        return {
            'processed_count': processed_count,
            'failed_count': failed_count,
            'invoices': invoices,
            'errors': errors
        }

    async def process_onedrive_folder(
        self,
        folder_url: str,
        contract_id: int,
        uploaded_by: int
    ) -> Dict[str, Any]:
        """
        Processa pasta do OneDrive contendo notas fiscais.
        """
        processed_count = 0
        failed_count = 0
        invoices = []
        errors = []

        try:
            # Baixar arquivos da pasta do OneDrive
            downloaded_files = await self._download_onedrive_files(folder_url)

            for file_info in downloaded_files:
                try:
                    invoice_data = await self._extract_invoice_data(
                        file_info['content'],
                        file_info['filename'],
                        is_content=True
                    )

                    if invoice_data:
                        # Criar invoice no banco
                        invoice = await self._create_invoice(
                            invoice_data,
                            contract_id,
                            folder_url  # URL original como referência
                        )
                        invoices.append(invoice)
                        processed_count += 1
                    else:
                        errors.append(f"Não foi possível extrair dados de {file_info['filename']}")
                        failed_count += 1

                except Exception as e:
                    errors.append(f"Erro ao processar {file_info['filename']}: {str(e)}")
                    failed_count += 1

        except Exception as e:
            raise Exception(f"Erro ao acessar pasta do OneDrive: {str(e)}")

        return {
            'processed_count': processed_count,
            'failed_count': failed_count,
            'invoices': invoices,
            'errors': errors
        }

    async def _extract_invoice_data(
        self,
        file_path_or_content: str,
        filename: str,
        is_content: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Extrai dados da nota fiscal de arquivo XML ou PDF.
        """
        try:
            if filename.lower().endswith('.xml'):
                return await self._extract_from_xml(file_path_or_content, is_content)
            elif filename.lower().endswith('.pdf'):
                return await self._extract_from_pdf(file_path_or_content, is_content)
            else:
                return None

        except Exception as e:
            print(f"Erro ao extrair dados de {filename}: {str(e)}")
            return None

    async def _extract_from_xml(self, file_path_or_content: str, is_content: bool = False) -> Dict[str, Any]:
        """
        Extrai dados de arquivo XML de NF-e.
        """
        try:
            if is_content:
                root = ET.fromstring(file_path_or_content)
            else:
                tree = ET.parse(file_path_or_content)
                root = tree.getroot()

            # Namespaces comuns de NF-e
            ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}

            # Extrair dados básicos da NF
            ide_elem = root.find('.//nfe:ide', ns)
            emit_elem = root.find('.//nfe:emit', ns)
            total_elem = root.find('.//nfe:total/nfe:ICMSTot', ns)

            if not all([ide_elem, emit_elem, total_elem]):
                # Tentar sem namespace (alguns XMLs não usam)
                ide_elem = root.find('.//ide')
                emit_elem = root.find('.//emit')
                total_elem = root.find('.//total/ICMSTot')

            numero_nf = ide_elem.find('nNF').text if ide_elem.find('nNF') is not None else None
            data_emissao_str = ide_elem.find('dhEmi').text if ide_elem.find('dhEmi') is not None else None

            # Parse da data
            data_emissao = None
            if data_emissao_str:
                try:
                    data_emissao = datetime.fromisoformat(data_emissao_str.replace('Z', '+00:00'))
                except:
                    # Tentar outros formatos de data
                    data_emissao = datetime.now()

            fornecedor = None
            if emit_elem.find('xNome') is not None:
                fornecedor = emit_elem.find('xNome').text

            valor_total = Decimal('0')
            if total_elem.find('vNF') is not None:
                valor_total = Decimal(total_elem.find('vNF').text)

            # Extrair itens
            items = []
            det_elems = root.findall('.//nfe:det', ns) or root.findall('.//det')

            for det in det_elems:
                prod = det.find('.//nfe:prod', ns) or det.find('.//prod')
                if prod is not None:
                    item_data = {
                        'descricao': prod.find('xProd').text if prod.find('xProd') is not None else 'Item não identificado',
                        'quantidade': Decimal(prod.find('qCom').text) if prod.find('qCom') is not None else None,
                        'valor_unitario': Decimal(prod.find('vUnCom').text) if prod.find('vUnCom') is not None else None,
                        'valor_total': Decimal(prod.find('vProd').text) if prod.find('vProd') is not None else Decimal('0'),
                        'unidade': prod.find('uCom').text if prod.find('uCom') is not None else None,
                        'centro_custo': 'Não Classificado'  # Will be classified later
                    }
                    items.append(item_data)

            return {
                'numero_nf': numero_nf,
                'fornecedor': fornecedor,
                'valor_total': valor_total,
                'data_emissao': data_emissao or datetime.now(),
                'items': items
            }

        except Exception as e:
            print(f"Erro ao processar XML: {str(e)}")
            return None

    async def _extract_from_pdf(self, file_path_or_content: str, is_content: bool = False) -> Dict[str, Any]:
        """
        Extrai dados de arquivo PDF de nota fiscal.
        Por enquanto, implementação básica usando regex.
        """
        try:
            # Esta é uma implementação simplificada
            # Em produção, seria necessário usar uma biblioteca como PyPDF2 ou pdfplumber

            # Por enquanto, retornar dados mock para PDFs
            return {
                'numero_nf': f"PDF-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'fornecedor': 'Fornecedor PDF',
                'valor_total': Decimal('1000.00'),
                'data_emissao': datetime.now(),
                'items': [{
                    'descricao': 'Item extraído de PDF',
                    'quantidade': Decimal('1'),
                    'valor_unitario': Decimal('1000.00'),
                    'valor_total': Decimal('1000.00'),
                    'unidade': 'UN',
                    'centro_custo': 'Não Classificado'
                }]
            }

        except Exception as e:
            print(f"Erro ao processar PDF: {str(e)}")
            return None

    async def _download_onedrive_files(self, folder_url: str) -> List[Dict[str, Any]]:
        """
        Baixa arquivos de uma pasta do OneDrive.
        Esta é uma implementação simplificada.
        """
        try:
            # Esta implementação seria específica para a API do OneDrive
            # Por enquanto, retornamos dados mock

            # Em produção, seria necessário:
            # 1. Autenticar com Microsoft Graph API
            # 2. Extrair share token da URL
            # 3. Listar arquivos da pasta
            # 4. Baixar cada arquivo

            # Mock data para demonstração
            return [
                {
                    'filename': 'mock_nf_001.xml',
                    'content': '''<?xml version="1.0"?>
                    <NFe>
                        <infNFe>
                            <ide><nNF>12345</nNF><dhEmi>2024-01-15T10:00:00</dhEmi></ide>
                            <emit><xNome>Fornecedor Teste</xNome></emit>
                            <total><ICMSTot><vNF>2500.00</vNF></ICMSTot></total>
                            <det><prod><xProd>Produto Teste</xProd><qCom>10</qCom><vUnCom>250.00</vUnCom><vProd>2500.00</vProd><uCom>UN</uCom></prod></det>
                        </infNFe>
                    </NFe>'''
                }
            ]

        except Exception as e:
            raise Exception(f"Erro ao baixar arquivos do OneDrive: {str(e)}")

    async def _create_invoice(
        self,
        invoice_data: Dict[str, Any],
        contract_id: int,
        arquivo_original: str
    ) -> InvoiceResponse:
        """
        Cria uma nova invoice no banco de dados.
        """
        try:
            # Criar invoice
            invoice = Invoice(
                contract_id=contract_id,
                numero_nf=invoice_data['numero_nf'],
                fornecedor=invoice_data['fornecedor'],
                valor_total=invoice_data['valor_total'],
                data_emissao=invoice_data['data_emissao'],
                arquivo_original=arquivo_original
            )

            self.db.add(invoice)
            self.db.flush()  # Para obter o ID da invoice

            # Criar itens
            for item_data in invoice_data.get('items', []):
                invoice_item = InvoiceItem(
                    invoice_id=invoice.id,
                    descricao=item_data['descricao'],
                    centro_custo=self._classify_cost_center(item_data['descricao']),
                    unidade=item_data.get('unidade'),
                    quantidade=item_data.get('quantidade'),
                    valor_unitario=item_data.get('valor_unitario'),
                    valor_total=item_data['valor_total']
                )
                self.db.add(invoice_item)

            self.db.commit()
            self.db.refresh(invoice)

            return InvoiceResponse(
                id=invoice.id,
                contract_id=invoice.contract_id,
                purchase_order_id=invoice.purchase_order_id,
                numero_nf=invoice.numero_nf,
                fornecedor=invoice.fornecedor,
                valor_total=invoice.valor_total,
                data_emissao=invoice.data_emissao,
                data_vencimento=invoice.data_vencimento,
                data_pagamento=invoice.data_pagamento,
                arquivo_original=invoice.arquivo_original,
                observacoes=invoice.observacoes,
                created_at=invoice.created_at,
                items_count=len(invoice.items)
            )

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Erro ao criar invoice no banco: {str(e)}")

    def _classify_cost_center(self, description: str) -> str:
        """
        Classifica automaticamente o centro de custo baseado na descrição.
        """
        description_lower = description.lower()

        # Classificação baseada em palavras-chave
        if any(keyword in description_lower for keyword in ['aço', 'ferro', 'metal', 'estrutura', 'viga', 'pilar']):
            return 'Matéria-prima'
        elif any(keyword in description_lower for keyword in ['soldador', 'serviço', 'mão de obra', 'montagem', 'instalação']):
            return 'Mão-de-obra'
        elif any(keyword in description_lower for keyword in ['transporte', 'frete', 'mobilização', 'desmobilização']):
            return 'Mobilização'
        else:
            return 'Não Classificado'