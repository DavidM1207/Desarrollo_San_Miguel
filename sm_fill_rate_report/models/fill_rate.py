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
        """Genera los datos del fill rate desde stock.move"""
        self.search([]).unlink()
        
        # Buscar todos los movimientos con requisition_order y estado done
        all_moves = self.env['stock.move'].search([
            ('requisition_order', '!=', False),
            ('state', '=', 'done')
        ])
        
        # Agrupar por requisition_order
        requisition_names = list(set(all_moves.mapped('requisition_order')))
        
        for req_name in requisition_names:
            # Buscar la requisición para obtener create_date
            requisition = self.env['employee.purchase.requisition'].search([
                ('name', '=', req_name)
            ], limit=1)
            
            if not requisition:
                continue
            
            # Filtrar movimientos de esta requisición
            req_moves = all_moves.filtered(lambda m: m.requisition_order == req_name)
            
            # Separar movimientos ORIGEN (internal -> transit)
            origin_moves = req_moves.filtered(
                lambda m: m.usage_origin == 'internal' and m.usage_dest == 'transit'
            )
            
            # Separar movimientos DESTINO (transit -> internal)
            dest_moves = req_moves.filtered(
                lambda m: m.usage_origin == 'transit' and m.usage_dest == 'internal'
            )
            
            if not origin_moves or not dest_moves:
                continue
            
            # Obtener productos únicos
            products = origin_moves.mapped('product_id')
            
            for product in products:
                # Movimientos de este producto
                origin_product = origin_moves.filtered(lambda m: m.product_id.id == product.id)
                dest_product = dest_moves.filtered(lambda m: m.product_id.id == product.id)
                
                # DEMANDA = suma de quantity del origen
                total_demand = sum(origin_product.mapped('quantity'))
                
                # RECIBIDO = suma de quantity del destino
                total_received = sum(dest_product.mapped('quantity'))
                
                if total_demand <= 0:
                    continue
                
                # Calcular fill rate
                fill_rate = (total_received / total_demand) * 100
                
                # Crear registro
                self.create({
                    'create_date': requisition.create_date,
                    'requisition_name': req_name,
                    'product_id': product.id,
                    'fill_rate_percentage': fill_rate,
                })
        
        return True