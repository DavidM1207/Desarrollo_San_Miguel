# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class FillRateReport(models.Model):
    _name = 'fill.rate.report'
    _description = 'Reporte de Fill Rate'
    _order = 'create_date desc'
    _rec_name = 'requisition_name'

    create_date = fields.Datetime(string='Fecha de Creación', readonly=True)
    requisition_id = fields.Many2one('employee.purchase.requisition', string='Requisición', readonly=True, ondelete='cascade')
    requisition_name = fields.Char(string='Nombre de Requisición', readonly=True)
    product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    cantidad_demandada = fields.Float(string='Cantidad Demandada', readonly=True)
    cantidad_recepcionada = fields.Float(string='Cantidad Recepcionada', readonly=True)
    fill_rate = fields.Float(string='% Fill Rate', readonly=True)
    stock_move_id = fields.Many2one('stock.move', string='Movimiento', readonly=True, ondelete='cascade')

    @api.model
    def _generate_report_data(self):
        """Genera los datos del reporte desde employee_purchase_requisition y stock.move"""
        _logger.info("Iniciando generación de reporte Fill Rate...")
        
        # Limpiar registros existentes
        old_records = self.search([])
        old_records.unlink()
        _logger.info(f"Eliminados {len(old_records)} registros antiguos")
        
        # Buscar todas las requisiciones
        requisitions = self.env['employee.purchase.requisition'].search([])
        _logger.info(f"Encontradas {len(requisitions)} requisiciones")
        
        records_created = 0
        
        for requisition in requisitions:
            # Verificar que la requisición tenga nombre
            if not requisition.name:
                _logger.warning(f"Requisición ID {requisition.id} sin nombre, omitiendo...")
                continue
            
            _logger.info(f"Procesando requisición: {requisition.name}")
            
            # Buscar pickings relacionados con esta requisición por el campo requisition_order
            pickings = self.env['stock.picking'].search([
                ('requisition_order', '=', requisition.name)
            ])
            
            _logger.info(f"  Pickings encontrados para {requisition.name}: {len(pickings)}")
            
            # Si no hay pickings por name, intentar por ID
            if not pickings:
                pickings = self.env['stock.picking'].search([
                    ('requisition_order', '=', str(requisition.id))
                ])
                _logger.info(f"  Pickings por ID para {requisition.name}: {len(pickings)}")
            
            # Si tiene relación directa con pickings internos
            if hasattr(requisition, 'internal_in_picking_id') and requisition.internal_in_picking_id:
                pickings |= requisition.internal_in_picking_id
                _logger.info(f"  Agregado internal_in_picking_id")
            
            if hasattr(requisition, 'internal_picking_id') and requisition.internal_picking_id:
                pickings |= requisition.internal_picking_id
                _logger.info(f"  Agregado internal_picking_id")
            
            # Obtener todos los movimientos de los pickings encontrados
            for picking in pickings:
                moves = picking.move_ids.filtered(lambda m: m.state == 'done')
                _logger.info(f"    Picking {picking.name}: {len(moves)} movimientos done")
                
                for move in moves:
                    # Validar que el movimiento y producto existen
                    if not move.exists() or not move.product_id.exists():
                        _logger.warning(f"    Move {move.id} o su producto no existe, omitiendo...")
                        continue
                    
                    cantidad_demandada = move.product_uom_qty or 0.0
                    cantidad_recepcionada = move.quantity or 0.0
                    
                    if cantidad_demandada > 0:
                        fill_rate = (cantidad_recepcionada / cantidad_demandada) * 100.0
                    else:
                        fill_rate = 0.0
                    
                    try:
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
                        records_created += 1
                        _logger.info(f"    ✓ Creado: {requisition.name} - {move.product_id.name} - Fill Rate: {fill_rate:.2f}%")
                    except Exception as e:
                        _logger.error(f"    ✗ Error creando registro para move {move.id}: {str(e)}")
        
        _logger.info(f"=== Generación completada. Total registros creados: {records_created} ===")
        return True

    @api.model
    def action_refresh_report(self):
        """Acción para refrescar el reporte"""
        self._generate_report_data()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }