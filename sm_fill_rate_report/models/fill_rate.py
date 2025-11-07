from odoo import models, fields, api


class FillRate(models.Model):
    _name = 'fill.rate'
    _description = 'Fill Rate'
    _order = 'create_date desc'

    create_date = fields.Datetime(string='Fecha de Creación')
    requisition_name = fields.Char(string='Número de Requisición')
    product_id = fields.Many2one('product.product', string='Producto')
    fill_rate_percentage = fields.Float(string='% Fill Rate', digits=(5, 2))

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """Generar datos automáticamente al abrir la vista"""
        self.generate_fill_rate_data()
        return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def generate_fill_rate_data(self):
        """Genera los datos del fill rate desde las requisiciones"""
        self.search([]).unlink()
        
        requisitions = self.env['employee.purchase.requisition'].search([])
        
        for requisition in requisitions:
            # Buscar picking ORIGEN (internal -> transit) en estado 'done'
            origin_picking = self.env['stock.picking'].search([
                ('requisition_order', '=', requisition.name),
                ('location_id.usage', '=', 'internal'),
                ('location_dest_id.usage', '=', 'transit'),
                ('state', '=', 'done')
            ], limit=1)
            
            # Buscar picking DESTINO (transit -> internal) en estado 'done'
            dest_picking = self.env['stock.picking'].search([
                ('requisition_order', '=', requisition.name),
                ('location_id.usage', '=', 'transit'),
                ('location_dest_id.usage', '=', 'internal'),
                ('state', '=', 'done')
            ], limit=1)
            
            if not origin_picking or not dest_picking:
                continue
            
            # Obtener movimientos de ambos pickings
            origin_moves = origin_picking.move_ids_without_package
            dest_moves = dest_picking.move_ids_without_package
            
            # Obtener productos únicos
            products = origin_moves.mapped('product_id')
            
            for product in products:
                # Movimientos de este producto en origen
                origin_product_moves = origin_moves.filtered(lambda m: m.product_id.id == product.id)
                # Movimientos de este producto en destino
                dest_product_moves = dest_moves.filtered(lambda m: m.product_id.id == product.id)
                
                # DEMANDA = quantity del origen (lo que salió)
                total_demand = sum(origin_product_moves.mapped('quantity'))
                
                # RECIBIDO = quantity del destino (lo que llegó)
                total_received = sum(dest_product_moves.mapped('quantity'))
                
                # Calcular fill rate
                fill_rate = 0.0
                if total_demand > 0:
                    fill_rate = (total_received / total_demand) * 100
                
                # Crear registro
                self.create({
                    'create_date': requisition.create_date,
                    'requisition_name': requisition.name,
                    'product_id': product.id,
                    'fill_rate_percentage': fill_rate,
                })
        
        return True