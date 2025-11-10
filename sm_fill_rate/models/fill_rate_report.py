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
        string='Requisiciones'
    )
    product_ids = fields.Many2many(
        'product.product',
        string='Productos'
    )

    def action_generate_report(self):
        self.ensure_one()
        
        if self.date_from > self.date_to:
            raise UserError(_('La fecha "Desde" no puede ser mayor que la fecha "Hasta".'))
        
        # Limpiar registros anteriores
        self.env['fill.rate.report.line'].search([
            ('create_uid', '=', self.env.uid)
        ]).unlink()
        
        # Generar líneas
        self._generate_report_lines()
        
        return {
            'name': _('Reporte de Fill Rate'),
            'type': 'ir.actions.act_window',
            'res_model': 'fill.rate.report.line',
            'view_mode': 'tree,graph,pivot',
            'domain': [('create_uid', '=', self.env.uid)],
            'context': {'search_default_group_by_requisition': 1},
            'target': 'current',
        }
    
    def _generate_report_lines(self):
        # Buscar pickings de destino validados
        picking_domain = [
            ('state', '=', 'done'),
            ('requisition_order', '!=', False),
            ('location_id.usage', '=', 'transit'),
            ('location_dest_id.usage', '=', 'internal'),
            ('date_done', '>=', self.date_from),
            ('date_done', '<=', self.date_to),
        ]
        
        if self.requisition_ids:
            picking_domain.append(('requisition_order', 'in', self.requisition_ids.mapped('name')))
        
        pickings = self.env['stock.picking'].search(picking_domain)
        
        report_lines = []
        processed = set()
        
        for picking in pickings:
            requisition = self.env['employee.purchase.requisition'].search([
                ('name', '=', picking.requisition_order)
            ], limit=1)
            
            if not requisition:
                continue
            
            origin_picking = self.env['stock.picking'].search([
                ('requisition_order', '=', picking.requisition_order),
                ('location_id.usage', '=', 'internal'),
                ('location_dest_id.usage', '=', 'transit'),
                ('state', '=', 'done'),
                ('backorder_id', '=', picking.backorder_id.id if picking.backorder_id else False),
            ], limit=1)
            
            for dest_move in picking.move_ids_without_package.filtered(lambda m: m.state == 'done'):
                if self.product_ids and dest_move.product_id not in self.product_ids:
                    continue
                
                combo_key = (requisition.id, dest_move.product_id.id, picking.id)
                if combo_key in processed:
                    continue
                processed.add(combo_key)
                
                req_line = requisition.requisition_order_ids.filtered(
                    lambda l: l.product_id.id == dest_move.product_id.id
                )
                
                if not req_line:
                    continue
                
                original_qty = sum(req_line.mapped('quantity'))
                
                sent_qty = 0.0
                if origin_picking:
                    origin_move = origin_picking.move_ids_without_package.filtered(
                        lambda m: m.product_id.id == dest_move.product_id.id and m.state == 'done'
                    )
                    sent_qty = sum(origin_move.mapped('quantity'))
                
                received_qty = dest_move.quantity
                
                fill_rate = 0.0
                if original_qty > 0:
                    fill_rate = (received_qty / original_qty) * 100
                
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
                    'location_dest_id': picking.location_dest_id.id,
                })
        
        if report_lines:
            self.env['fill.rate.report.line'].create(report_lines)
        else:
            raise UserError(_('No se encontraron datos para los filtros seleccionados.'))


class FillRateReportLine(models.TransientModel):
    _name = 'fill.rate.report.line'
    _description = 'Linea de Reporte de Fill Rate'
    _order = 'requisition_date desc, requisition_name, product_id'

    requisition_id = fields.Many2one('employee.purchase.requisition', string='Requisicion', readonly=True)
    requisition_name = fields.Char(string='Nombre Requisicion', readonly=True)
    requisition_date = fields.Datetime(string='Fecha Creacion', readonly=True)
    product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    original_qty = fields.Float(string='Cantidad Original', readonly=True, digits='Product Unit of Measure')
    sent_qty = fields.Float(string='Cantidad Enviada', readonly=True, digits='Product Unit of Measure')
    received_qty = fields.Float(string='Cantidad Recibida', readonly=True, digits='Product Unit of Measure')
    fill_rate = fields.Float(string='Fill Rate (%)', readonly=True, digits=(16, 2), group_operator='avg')
    uom_id = fields.Many2one('uom.uom', string='Unidad de Medida', readonly=True)
    picking_origin_id = fields.Many2one('stock.picking', string='Traslado Origen', readonly=True)
    picking_dest_id = fields.Many2one('stock.picking', string='Traslado Destino', readonly=True)
    location_dest_id = fields.Many2one('stock.location', string='Ubicacion Destino', readonly=True)
    
    fill_rate_category = fields.Selection([
        ('excellent', 'Excelente (>=95%)'),
        ('good', 'Bueno (80-94%)'),
        ('regular', 'Regular (60-79%)'),
        ('poor', 'Deficiente (<60%)'),
    ], string='Categoria Fill Rate', compute='_compute_fill_rate_category', store=True)
    
    variance_qty = fields.Float(string='Variacion', compute='_compute_variance', digits='Product Unit of Measure')
    variance_percentage = fields.Float(string='Variacion (%)', compute='_compute_variance', digits=(16, 2))

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
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Requisicion'),
            'res_model': 'employee.purchase.requisition',
            'res_id': self.requisition_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_picking_origin(self):
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
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Traslado Destino'),
            'res_model': 'stock.picking',
            'res_id': self.picking_dest_id.id,
            'view_mode': 'form',
            'target': 'current',
        }