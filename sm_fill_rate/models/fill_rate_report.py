# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class FillRateReportWizard(models.TransientModel):
    _name = 'fill.rate.report.wizard'
    _description = 'Asistente para Reporte de Fill Rate'

    date_from = fields.Date(
        string='Fecha Desde',
        required=True,
        default=fields.Date.context_today
    )
    date_to = fields.Date(
        string='Fecha Hasta',
        required=True,
        default=fields.Date.context_today
    )
    requisition_ids = fields.Many2many(
        'employee.purchase.requisition',
        string='Requisiciones',
        help='Dejar vacío para incluir todas las requisiciones'
    )
    product_ids = fields.Many2many(
        'product.product',
        string='Productos',
        help='Dejar vacío para incluir todos los productos'
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Ubicación Destino',
        help='Filtrar por ubicación destino (transit -> internal)'
    )
    fill_rate_threshold = fields.Float(
        string='Fill Rate Mínimo (%)',
        default=0.0,
        help='Mostrar solo productos con fill rate mayor o igual a este porcentaje'
    )

    def action_generate_report(self):
        """Genera el reporte de Fill Rate"""
        self.ensure_one()
        
        # Validar fechas
        if self.date_from > self.date_to:
            raise UserError(_('La fecha "Desde" no puede ser mayor que la fecha "Hasta".'))
        
        # Limpiar registros anteriores del usuario actual
        self.env['fill.rate.report.line'].search([
            ('create_uid', '=', self.env.uid)
        ]).unlink()
        
        # Generar las líneas del reporte
        self._generate_report_lines()
        
        # Retornar acción para mostrar el reporte
        return {
            'name': _('Reporte de Fill Rate'),
            'type': 'ir.actions.act_window',
            'res_model': 'fill.rate.report.line',
            'view_mode': 'tree,graph,pivot',
            'domain': [('create_uid', '=', self.env.uid)],
            'context': {
                'search_default_group_by_requisition': 1,
            },
            'target': 'current',
        }
    
    def _generate_report_lines(self):
        """Genera las líneas del reporte con el cálculo de Fill Rate"""
        
        # Construir dominio para pickings
        picking_domain = [
            ('state', '=', 'done'),
            ('requisition_order', '!=', False),
            ('location_id.usage', '=', 'transit'),
            ('location_dest_id.usage', '=', 'internal'),
            ('date_done', '>=', self.date_from),
            ('date_done', '<=', self.date_to),
        ]
        
        if self.location_id:
            picking_domain.append(('location_dest_id', '=', self.location_id.id))
        
        if self.requisition_ids:
            picking_domain.append(('requisition_order', 'in', self.requisition_ids.mapped('name')))
        
        # Buscar pickings validados (destino: transit -> internal)
        pickings = self.env['stock.picking'].search(picking_domain)
        
        report_lines = []
        processed_combinations = set()  # Para evitar duplicados
        
        for picking in pickings:
            # Buscar la requisición original
            requisition = self.env['employee.purchase.requisition'].search([
                ('name', '=', picking.requisition_order)
            ], limit=1)
            
            if not requisition:
                continue
            
            # Buscar el picking origen (internal -> transit)
            origin_picking = self.env['stock.picking'].search([
                ('requisition_order', '=', picking.requisition_order),
                ('location_id.usage', '=', 'internal'),
                ('location_dest_id.usage', '=', 'transit'),
                ('state', '=', 'done'),
                ('backorder_id', '=', picking.backorder_id.id if picking.backorder_id else False),
            ], limit=1)
            
            # Procesar cada movimiento del picking de destino
            for dest_move in picking.move_ids_without_package.filtered(lambda m: m.state == 'done'):
                # Filtrar por productos si se especificaron
                if self.product_ids and dest_move.product_id not in self.product_ids:
                    continue
                
                # Evitar duplicados por combinación única
                combination_key = (
                    requisition.id,
                    dest_move.product_id.id,
                    picking.id
                )
                
                if combination_key in processed_combinations:
                    continue
                
                processed_combinations.add(combination_key)
                
                # Buscar la línea de requisición para obtener la cantidad original
                req_line = requisition.requisition_order_ids.filtered(
                    lambda l: l.product_id.id == dest_move.product_id.id
                )
                
                if not req_line:
                    continue
                
                # Obtener cantidades
                original_qty = sum(req_line.mapped('quantity'))  # Cantidad original de la requisición
                
                # Cantidad enviada del picking origen
                sent_qty = 0.0
                if origin_picking:
                    origin_move = origin_picking.move_ids_without_package.filtered(
                        lambda m: m.product_id.id == dest_move.product_id.id and m.state == 'done'
                    )
                    sent_qty = sum(origin_move.mapped('quantity'))
                
                # Cantidad recibida (validada en destino)
                received_qty = dest_move.quantity
                
                # Calcular Fill Rate
                # Fill Rate = (Cantidad Recibida / Cantidad Original) × 100
                fill_rate = 0.0
                if original_qty > 0:
                    fill_rate = (received_qty / original_qty) * 100
                
                # Filtrar por fill rate mínimo
                if fill_rate < self.fill_rate_threshold:
                    continue
                
                # Crear línea del reporte
                report_lines.append({
                    'requisition_id': requisition.id,
                    'requisition_name': requisition.name,
                    'requisition_date': requisition.create_date,
                    'product_id': dest_move.product_id.id,
                    'original_qty': original_qty,
                    'sent_qty': sent_qty,
                    'received_qty': received_qty,
                    'fill_rate': fill_rate,
                    'uom_id': dest_move.product_uom.id,
                    'picking_origin_id': origin_picking.id if origin_picking else False,
                    'picking_dest_id': picking.id,
                    'location_origin_id': origin_picking.location_id.id if origin_picking else False,
                    'location_dest_id': picking.location_dest_id.id,
                })
        
        # Crear todas las líneas en batch
        if report_lines:
            self.env['fill.rate.report.line'].create(report_lines)
        else:
            raise UserError(_('No se encontraron datos para los filtros seleccionados.'))


class FillRateReportLine(models.TransientModel):
    _name = 'fill.rate.report.line'
    _description = 'Línea de Reporte de Fill Rate'
    _order = 'requisition_date desc, requisition_name, product_id'
    _rec_name = 'requisition_name'

    requisition_id = fields.Many2one(
        'employee.purchase.requisition',
        string='Requisición',
        readonly=True
    )
    requisition_name = fields.Char(
        string='Nombre Requisición',
        readonly=True,
        index=True
    )
    requisition_date = fields.Datetime(
        string='Fecha Creación',
        readonly=True,
        index=True
    )
    product_id = fields.Many2one(
        'product.product',
        string='Producto',
        readonly=True,
        index=True
    )
    original_qty = fields.Float(
        string='Cantidad Original',
        readonly=True,
        digits='Product Unit of Measure',
        help='Cantidad solicitada en la requisición original'
    )
    sent_qty = fields.Float(
        string='Cantidad Enviada',
        readonly=True,
        digits='Product Unit of Measure',
        help='Cantidad enviada desde origen (internal → transit)'
    )
    received_qty = fields.Float(
        string='Cantidad Recibida',
        readonly=True,
        digits='Product Unit of Measure',
        help='Cantidad recibida en destino (transit → internal)'
    )
    fill_rate = fields.Float(
        string='Fill Rate (%)',
        readonly=True,
        digits=(16, 2),
        group_operator='avg',
        help='Porcentaje de cumplimiento = (Cantidad Recibida / Cantidad Original) × 100'
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unidad de Medida',
        readonly=True
    )
    picking_origin_id = fields.Many2one(
        'stock.picking',
        string='Traslado Origen',
        readonly=True
    )
    picking_dest_id = fields.Many2one(
        'stock.picking',
        string='Traslado Destino',
        readonly=True
    )
    location_origin_id = fields.Many2one(
        'stock.location',
        string='Ubicación Origen',
        readonly=True
    )
    location_dest_id = fields.Many2one(
        'stock.location',
        string='Ubicación Destino',
        readonly=True
    )
    fill_rate_category = fields.Selection([
        ('excellent', 'Excelente (≥95%)'),
        ('good', 'Bueno (80-94%)'),
        ('regular', 'Regular (60-79%)'),
        ('poor', 'Deficiente (<60%)'),
    ], string='Categoría Fill Rate', compute='_compute_fill_rate_category', store=True)
    
    variance_qty = fields.Float(
        string='Variación',
        compute='_compute_variance',
        digits='Product Unit of Measure',
        help='Diferencia entre cantidad recibida y cantidad original'
    )
    variance_percentage = fields.Float(
        string='Variación (%)',
        compute='_compute_variance',
        digits=(16, 2),
        help='Porcentaje de variación respecto a la cantidad original'
    )

    @api.depends('fill_rate')
    def _compute_fill_rate_category(self):
        for line in self:
            if line.fill_rate >= 95:
                line.fill_rate_category = 'excellent'
            elif line.fill_rate >= 80:
                line.fill_rate_category = 'good'
            elif line.fill_rate >= 60:
                line.fill_rate_category = 'regular'
            else:
                line.fill_rate_category = 'poor'
    
    @api.depends('original_qty', 'received_qty')
    def _compute_variance(self):
        for line in self:
            line.variance_qty = line.received_qty - line.original_qty
            if line.original_qty > 0:
                line.variance_percentage = (line.variance_qty / line.original_qty) * 100
            else:
                line.variance_percentage = 0.0

    def action_view_requisition(self):
        """Abrir la requisición relacionada"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Requisición'),
            'res_model': 'employee.purchase.requisition',
            'res_id': self.requisition_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_picking_origin(self):
        """Abrir el traslado origen"""
        self.ensure_one()
        if not self.picking_origin_id:
            raise UserError(_('No hay traslado origen asociado.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Traslado Origen'),
            'res_model': 'stock.picking',
            'res_id': self.picking_origin_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_picking_dest(self):
        """Abrir el traslado destino"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Traslado Destino'),
            'res_model': 'stock.picking',
            'res_id': self.picking_dest_id.id,
            'view_mode': 'form',
            'target': 'current',
        }