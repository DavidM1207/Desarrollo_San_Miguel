# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError

class StockPicking(models.Model):
    _inherit= "stock.picking"

    def button_validate(self):
        for picking in self:
            if picking.requisition_order:
                if picking.location_id.usage == 'transit' and picking.location_dest_id.usage == 'internal' and not picking.backorder_id:
                    previous_picking = self.env['stock.picking'].search([
                        ('requisition_order', '=', picking.requisition_order),
                        ('location_id.usage', '=', 'internal'),
                        ('location_dest_id.usage', '=', 'transit'),
                        ('state', '!=', 'cancel'),
                        ('backorder_id', '=', False),  
                    ], limit=1)
                    
                    if not previous_picking:
                        raise UserError(_('No se encontró un traslado previo para esta requisición.'))

                    if previous_picking.state != 'done':
                        raise UserError(_('No puede validar este movimiento hasta que se haya completado el traslado desde Transferencia Origen.'))

                    # Validación modificada: agrupa por producto todas las líneas del picking anterior
                    for move in picking.move_ids_without_package:
                        # Buscar TODAS las líneas del producto en el picking anterior (no solo una)
                        prev_moves = previous_picking.move_ids_without_package.filtered(
                            lambda m: m.product_id.id == move.product_id.id
                        )
                        
                        if prev_moves:
                            # Sumar TODAS las cantidades del mismo producto (incluyendo líneas divididas)
                            prev_qty_total = sum(prev_moves.mapped('quantity'))
                            
                            if move.quantity != prev_qty_total:
                                raise UserError(_(
                                    'La cantidad del producto "%s" (%s) no coincide con la cantidad total del traslado previo (%s).'
                                ) % (move.product_id.display_name, move.quantity, prev_qty_total))
                
                if picking.location_id.usage == 'transit' and picking.location_dest_id.usage == 'internal' and picking.backorder_id:
                    previous_picking = self.env['stock.picking'].search([
                        ('requisition_order', '=', picking.requisition_order),
                        ('location_id.usage', '=', 'internal'),
                        ('location_dest_id.usage', '=', 'transit'),
                        ('state', '!=', 'cancel'),
                        ('backorder_id', '!=', False), 
                    ], limit=1)
                    
                    if not previous_picking:
                        raise UserError(_('No se encontró un traslado previo para esta requisición!.'))

                    if previous_picking.state != 'done':
                        raise UserError(_('No puede validar este movimiento hasta que se haya completado el traslado desde Transferencia Origen.!'))

                    # Validación modificada para backorders también
                    for move in picking.move_ids_without_package:
                        # Buscar TODAS las líneas del producto en el picking anterior
                        prev_moves = previous_picking.move_ids_without_package.filtered(
                            lambda m: m.product_id.id == move.product_id.id
                        )
                        
                        if prev_moves:
                            # Sumar TODAS las cantidades del mismo producto
                            prev_qty_total = sum(prev_moves.mapped('quantity'))
                            
                            if move.quantity != prev_qty_total:
                                raise UserError(_(
                                    'La cantidad del producto "%s" (%s) no coincide con la cantidad total del traslado previo (%s).'
                                ) % (move.product_id.display_name, move.quantity, prev_qty_total))

        return super(StockPicking, self).button_validate()


class StockMove(models.Model):
    _inherit= "stock.move"

    requisition_order = fields.Char(string='Requisición', readonly=True, copy=False, related='picking_id.requisition_order')
    usage_origin = fields.Selection(related='picking_id.location_id.usage', string='Uso de Ubicación Origen', readonly=True)
    usage_dest = fields.Selection(related='picking_id.location_dest_id.usage', string='Uso de Ubicación Destino', readonly=True)


    user_can_edit_quantity = fields.Boolean(
        string="Puede editar cantidad",
        compute='_compute_user_can_edit_quantity',
        store=False
    )
    
    @api.depends_context('uid')
    def _compute_user_can_edit_quantity(self):
        group_id = "dv_requisition_custom.group_requisition_quantity_manager"
        has_group = self.env.user.has_group(group_id)
        for move in self:
            move.user_can_edit_quantity = has_group

    @api.onchange('quantity')
    def _check_quantity_done(self):
        for move in self:            
            if move.quantity > move.product_uom_qty and move.usage_origin == 'internal' and move.usage_dest == 'transit' and move.requisition_order:
                # Buscar el movimiento relacionado en la recepción (transit -> internal)
                related_moves = self.env['stock.move'].search([
                    ('requisition_order', '=', move.requisition_order),
                    ('state', 'in', ['draft', 'waiting', 'confirmed']),
                    ('usage_origin', '=', 'transit'),
                    ('usage_dest', '=', 'internal'),
                    ('product_id', '=', move.product_id.id)
                ])
                
                if related_moves:
                    # Calcular el total enviado desde origen (todas las líneas del mismo producto)
                    origin_moves = self.env['stock.move'].search([
                        ('requisition_order', '=', move.requisition_order),
                        ('usage_origin', '=', 'internal'),
                        ('usage_dest', '=', 'transit'),
                        ('product_id', '=', move.product_id.id),
                        ('picking_id', '=', move.picking_id.id)
                    ])
                    
                    total_origin_qty = sum(origin_moves.mapped('quantity'))
                    
                    # Actualizar la cantidad en la recepción con el total consolidado
                    # Si hay una sola línea en recepción, actualizar esa
                    if len(related_moves) == 1:
                        related_moves[0].sudo().write({'product_uom_qty': total_origin_qty})
                    else:
                        # Si hay múltiples líneas en recepción, actualizar la primera y eliminar las demás
                        related_moves[0].sudo().write({'product_uom_qty': total_origin_qty})
                        related_moves[1:].sudo().unlink()

            if move.quantity > move.product_uom_qty and move.usage_origin == 'transit' and move.usage_dest == 'internal' and move.requisition_order:
                raise ValidationError(
                    _("La cantidad realizada (%s) no puede ser mayor que la cantidad demandada (%s) para el producto: %s") %
                    (move.quantity, move.product_uom_qty, move.product_id.display_name)
                )