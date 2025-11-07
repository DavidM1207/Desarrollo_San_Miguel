# -*- coding: utf-8 -*-
from odoo import models, fields, api

class FillRateReport(models.Model):
    _name = 'fill.rate.report'
    _description = 'Reporte de Fill Rate'
    _order = 'create_date desc'
    _rec_name = 'requisition_name'

    create_date = fields.Datetime(string='Fecha de Creación')
    requisition_id = fields.Many2one('employee.purchase.requisition', string='Requisición', ondelete='cascade')
    requisition_name = fields.Char(string='Nombre de Requisición')
    product_id = fields.Many2one('product.product', string='Producto')
    cantidad_demandada = fields.Float(string='Cantidad Demandada')
    cantidad_recepcionada = fields.Float(string='Cantidad Recepcionada')
    fill_rate = fields.Float(string='% Fill Rate')
    stock_move_id = fields.Many2one('stock.move', string='Movimiento', ondelete='cascade')

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """Override search_read para generar datos dinámicamente"""
        records = self.search([('stock_move_id', '!=', False)], limit=1)
        
        if not records:
            requisitions = self.env['employee.purchase.requisition'].search([])
            
            for requisition in requisitions:
                if not requisition.name:
                    continue
                
                pickings = self.env['stock.picking'].search([
                    ('requisition_order', '=', requisition.name)
                ])
                
                for picking in pickings:
                    moves = self.env['stock.move'].search([
                        ('picking_id', '=', picking.id),
                        ('state', '=', 'done')
                    ])
                    
                    for move in moves:
                        if not move.product_id:
                            continue
                        
                        cantidad_demandada = move.product_uom_qty or 0.0
                        cantidad_recepcionada = move.quantity or 0.0
                        
                        if cantidad_demandada > 0:
                            fill_rate = (cantidad_recepcionada / cantidad_demandada) * 100.0
                        else:
                            fill_rate = 0.0
                        
                        existing = self.search([('stock_move_id', '=', move.id)], limit=1)
                        
                        if not existing:
                            self.create({
                                'create_date': requisition.create_date,
                                'requisition_id': requisition.id,
                                'requisition_name': requisition.name,
                                'product_id': move.product_id.id,
                                'cantidad_demandada': cantidad_demandada,
                                'cantidad_recepcionada': cantidad_recepcionada,
                                'fill_rate': fill_rate,
                                'stock_move_id': move.id,
                            })
        
        return super(FillRateReport, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)


class EmployeePurchaseRequisition(models.Model):
    _inherit = 'employee.purchase.requisition'

    def write(self, vals):
        res = super(EmployeePurchaseRequisition, self).write(vals)
        self.env['fill.rate.report'].search([]).unlink()
        return res


class StockMove(models.Model):
    _inherit = 'stock.move'

    def write(self, vals):
        res = super(StockMove, self).write(vals)
        if 'state' in vals and vals.get('state') == 'done':
            self.env['fill.rate.report'].search([]).unlink()
        return res