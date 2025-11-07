from odoo import models, fields, api


class FillRate(models.Model):
    _name = 'fill.rate'
    _description = 'Fill Rate Report'
    _order = 'create_date desc'

    create_date = fields.Datetime(string='Fecha de Creación')
    requisition_name = fields.Char(string='Número de Requisición')
    product_id = fields.Many2one('product.product', string='Producto')
    demand_qty = fields.Float(string='Demanda')
    received_qty = fields.Float(string='Recibido')
    fill_rate_percentage = fields.Float(string='% Fill Rate', digits=(5, 2))

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        """Override para regenerar datos"""
        self.sudo().search([]).unlink()
        
        # Buscar movimientos done con requisition_order
        moves = self.env['stock.move'].sudo().search([
            ('requisition_order', '!=', False),
            ('state', '=', 'done')
        ])
        
        # Diccionario temporal para agrupar
        grouped = {}
        
        for move in moves:
            key = (move.requisition_order, move.product_id.id)
            
            if key not in grouped:
                req = self.env['employee.purchase.requisition'].sudo().search([
                    ('name', '=', move.requisition_order)
                ], limit=1)
                
                grouped[key] = {
                    'create_date': req.create_date if req else fields.Datetime.now(),
                    'requisition_name': move.requisition_order,
                    'product_id': move.product_id.id,
                    'total_origin': 0.0,
                    'total_dest': 0.0
                }
            
            # ORIGEN (internal -> transit): quantity = lo que salió
            if move.usage_origin == 'internal' and move.usage_dest == 'transit':
                grouped[key]['total_origin'] += move.quantity
                
            # DESTINO (transit -> internal): quantity = lo que llegó  
            elif move.usage_origin == 'transit' and move.usage_dest == 'internal':
                grouped[key]['total_dest'] += move.quantity
        
        # Crear registros
        for vals in grouped.values():
            if vals['total_origin'] > 0:
                self.sudo().create({
                    'create_date': vals['create_date'],
                    'requisition_name': vals['requisition_name'],
                    'product_id': vals['product_id'],
                    'demand_qty': vals['total_origin'],
                    'received_qty': vals['total_dest'],
                    'fill_rate_percentage': (vals['total_dest'] / vals['total_origin']) * 100
                })
        
        return super(FillRate, self).search(args, offset=offset, limit=limit, order=order, count=count)