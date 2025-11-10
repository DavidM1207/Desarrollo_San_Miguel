# -*- coding: utf-8 -*-

from odoo import api, fields, models


class EmployeePurchaseRequisitionFillrateReport(models.Model):
    _name = 'employee.purchase.requisition.fillrate.report'
    _description = 'Reporte Fill Rate de Requisiciones'
    _order = 'date_creation desc'

    date_creation = fields.Datetime(string='Fecha Creación', readonly=True)
    requisition_name = fields.Char(string='Nombre Requisición', readonly=True)
    requisition_id = fields.Many2one('employee.purchase.requisition', string='Requisición', readonly=True)
    product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    original_qty = fields.Float(string='Cantidad Original', readonly=True, digits='Product Unit of Measure')
    validated_qty = fields.Float(string='Cantidad Validada', readonly=True, digits='Product Unit of Measure')
    fill_rate = fields.Float(string='% Fill Rate', readonly=True, digits=(16, 2))
    picking_id = fields.Many2one('stock.picking', string='Traslado', readonly=True)
    move_id = fields.Many2one('stock.move', string='Movimiento', readonly=True)

    @api.model
    def _get_fillrate_data(self):
        """Obtener datos de fill rate desde requisiciones"""
        data = []
        
        requisitions = self.env['employee.purchase.requisition'].search([])
        
        for requisition in requisitions:
            pickings = self.env['stock.picking'].search([
                ('requisition_order', '=', requisition.name),
                ('state', '=', 'done'),
                ('location_id.usage', '=', 'internal'),
                ('location_dest_id.usage', '=', 'transit')
            ])
            
            for picking in pickings:
                moves = picking.move_ids_without_package.filtered(
                    lambda m: m.state == 'done'
                )
                
                for move in moves:
                    fill_rate = 0.0
                    if move.product_uom_qty > 0:
                        fill_rate = (move.quantity / move.product_uom_qty) * 100
                    
                    data.append({
                        'date_creation': requisition.create_date,
                        'requisition_name': requisition.name,
                        'requisition_id': requisition.id,
                        'product_id': move.product_id.id,
                        'original_qty': move.product_uom_qty,
                        'validated_qty': move.quantity,
                        'fill_rate': fill_rate,
                        'picking_id': picking.id,
                        'move_id': move.id,
                    })
        
        return data

    @api.model
    def action_refresh_data(self):
        """Refrescar datos del reporte"""
        self.search([]).unlink()
        
        data = self._get_fillrate_data()
        
        for vals in data:
            self.create(vals)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Éxito',
                'message': 'Datos actualizados correctamente',
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """Override para recalcular datos en agrupaciones"""
        self.action_refresh_data()
        return super(EmployeePurchaseRequisitionFillrateReport, self).read_group(
            domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy
        )

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """Override para refrescar datos antes de leer"""
        self.action_refresh_data()
        return super(EmployeePurchaseRequisitionFillrateReport, self).search_read(
            domain=domain, fields=fields, offset=offset, limit=limit, order=order
        )