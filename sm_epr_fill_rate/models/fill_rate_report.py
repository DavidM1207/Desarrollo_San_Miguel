# -*- coding: utf-8 -*-

from odoo import models, fields, api


class FillRateReport(models.Model):
    _name = 'employee.purchase.requisition.fill.rate.report'
    _description = 'Reporte Fill Rate de Requisiciones'
    _order = 'date_created desc'

    date_created = fields.Datetime(string='Fecha Creación', readonly=True)
    requisition_id = fields.Many2one('employee.purchase.requisition', string='Requisición', readonly=True)
    requisition_number = fields.Char(string='Número Requisición', readonly=True)
    product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    demand_type = fields.Char(string='Demanda', readonly=True)
    quantity_original = fields.Float(string='Cantidad Original (Unidades Solicitadas)', readonly=True, digits=(16, 2))
    quantity_delivered = fields.Float(string='Cantidad Demanda (Unidades Entregadas)', readonly=True, digits=(16, 2))
    fill_rate = fields.Float(string='Fill Rate (%)', readonly=True, digits=(16, 2))

    @api.model
    def _get_delivered_quantity(self, requisition_name, product_id):
        """Calcula la cantidad entregada basándose en los movimientos de stock"""
        moves = self.env['stock.move'].search([
            ('origin', '=', requisition_name),
            ('product_id', '=', product_id),
            ('state', '=', 'done')
        ])
        return sum(moves.mapped('product_uom_qty'))

    @api.model
    def _generate_report_data(self, domain=None):
        """Genera los datos del reporte dinámicamente"""
        if domain is None:
            domain = []
        
        # Buscar requisiciones de tipo transferencia interna
        req_domain = [('demand_type', '=', 'internal_transfer')]
        
        # Aplicar filtros adicionales si existen
        for item in domain:
            if isinstance(item, (list, tuple)) and len(item) == 3:
                field, operator, value = item
                if field == 'date_created':
                    req_domain.append(('create_date', operator, value))
                elif field == 'requisition_number':
                    req_domain.append(('name', operator, value))
        
        requisitions = self.env['employee.purchase.requisition'].search(req_domain)
        
        report_data = []
        for requisition in requisitions:
            for line in requisition.requisition_line_ids.filtered(lambda l: l.qty > 0):
                # Calcular cantidad entregada
                delivered_qty = self._get_delivered_quantity(requisition.name, line.product_id.id)
                
                # Calcular Fill Rate
                fill_rate = (delivered_qty / line.qty * 100) if line.qty > 0 else 0.0
                
                report_data.append({
                    'date_created': requisition.create_date,
                    'requisition_id': requisition.id,
                    'requisition_number': requisition.name,
                    'product_id': line.product_id.id,
                    'demand_type': requisition.demand_type,
                    'quantity_original': line.qty,
                    'quantity_delivered': delivered_qty,
                    'fill_rate': round(fill_rate, 2),
                })
        
        return report_data

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """Sobrescribir search_read para generar datos dinámicamente"""
        report_data = self._generate_report_data(domain)
        
        # Aplicar ordenamiento si se especifica
        if order:
            # Por defecto ya está ordenado por fecha descendente
            pass
        
        # Aplicar offset y limit
        if offset:
            report_data = report_data[offset:]
        if limit:
            report_data = report_data[:limit]
        
        # Filtrar campos si se especifican
        if fields:
            filtered_data = []
            for record in report_data:
                filtered_record = {k: v for k, v in record.items() if k in fields or k == 'id'}
                # Agregar ID ficticio
                filtered_record['id'] = hash(str(record.get('requisition_id', 0)) + str(record.get('product_id', 0)))
                filtered_data.append(filtered_record)
            return filtered_data
        
        # Agregar ID ficticio a cada registro
        for idx, record in enumerate(report_data):
            record['id'] = hash(str(record.get('requisition_id', 0)) + str(record.get('product_id', 0)))
        
        return report_data

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """Sobrescribir read_group para permitir agrupaciones"""
        report_data = self._generate_report_data(domain)
        
        if not groupby:
            return []
        
        # Implementación básica de agrupación
        grouped_data = {}
        groupby_field = groupby[0].split(':')[0] if ':' in groupby[0] else groupby[0]
        
        for record in report_data:
            key = record.get(groupby_field)
            if key not in grouped_data:
                grouped_data[key] = {
                    groupby_field: key,
                    '__count': 0,
                    'quantity_original': 0,
                    'quantity_delivered': 0,
                }
            
            grouped_data[key]['__count'] += 1
            grouped_data[key]['quantity_original'] += record.get('quantity_original', 0)
            grouped_data[key]['quantity_delivered'] += record.get('quantity_delivered', 0)
        
        return list(grouped_data.values())