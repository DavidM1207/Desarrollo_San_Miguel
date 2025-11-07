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
        import logging
        _logger = logging.getLogger(__name__)
        
        self.search([]).unlink()  # Limpiar datos anteriores
        
        requisitions = self.env['employee.purchase.requisition'].search([])
        _logger.info(f"Total requisiciones encontradas: {len(requisitions)}")
        
        for requisition in requisitions:
            _logger.info(f"Procesando requisición: {requisition.name}")
            
            # Obtener líneas de productos de la requisición
            requisition_lines = self.env['requisition.order'].search([
                ('requisition_id', '=', requisition.id)
            ])
            _logger.info(f"Líneas encontradas para {requisition.name}: {len(requisition_lines)}")
            
            for line in requisition_lines:
                _logger.info(f"Procesando producto: {line.product_id.name}")
                
                # Obtener pickings relacionados en estado 'done'
                done_pickings = requisition.requisition_order_ids.filtered(
                    lambda p: p.state == 'done'
                )
                _logger.info(f"Pickings en estado done: {len(done_pickings)}")
                
                if not done_pickings:
                    continue
                
                total_demand = 0.0
                total_received = 0.0
                
                # Recorrer los movimientos de los pickings
                for picking in done_pickings:
                    moves = picking.move_ids.filtered(
                        lambda m: m.product_id.id == line.product_id.id
                    )
                    _logger.info(f"Movimientos encontrados para {line.product_id.name}: {len(moves)}")
                    
                    for move in moves:
                        total_demand += move.product_uom_qty
                        total_received += move.quantity
                        _logger.info(f"Move - Demanda: {move.product_uom_qty}, Recibido: {move.quantity}")
                
                _logger.info(f"Total - Demanda: {total_demand}, Recibido: {total_received}")
                
                # Calcular fill rate
                fill_rate = 0.0
                if total_demand > 0:
                    fill_rate = (total_received / total_demand) * 100
                
                _logger.info(f"Fill Rate calculado: {fill_rate}%")
                
                # Crear registro
                self.create({
                    'create_date': requisition.create_date,
                    'requisition_name': requisition.name,
                    'product_id': line.product_id.id,
                    'fill_rate_percentage': fill_rate,
                })
        
        return True