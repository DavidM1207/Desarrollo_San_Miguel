# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        for picking in self:
            if picking.requisition_order:
                # Validar las cantidades ANTES de validar el picking
                for move in picking.move_ids_without_package:
                    # Validación para movimientos de internal a transit
                    if (move.usage_origin == 'internal' and 
                        move.usage_dest == 'transit' and 
                        move.state not in ('done', 'cancel')):
                        
                        if move.quantity != move.product_uom_qty:
                            raise UserError(
                                _("No puede validar el traslado. La cantidad realizada (%s) debe ser igual "
                                  "a la cantidad demandada (%s) para el producto: %s en el traslado de origen.") %
                                (move.quantity, move.product_uom_qty, move.product_id.display_name)
                            )
                    
                    # Validación para movimientos de transit a internal
                    if (move.quantity > move.product_uom_qty and 
                        move.usage_origin == 'transit' and 
                        move.usage_dest == 'internal' and 
                        move.state not in ('done', 'cancel')):
                        raise UserError(
                            _("No puede validar el traslado. La cantidad realizada (%s) no puede ser mayor "
                              "que la cantidad demandada (%s) para el producto: %s.") %
                            (move.quantity, move.product_uom_qty, move.product_id.display_name)
                        )
                
                # Validaciones existentes para traslados relacionados
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

                    for move in picking.move_ids_without_package:
                        prev_move = previous_picking.move_ids_without_package.filtered(lambda m: m.product_id.id == move.product_id.id)
                        if prev_move:
                            prev_qty = sum(prev_move.mapped('quantity'))
                            if move.quantity != prev_qty:
                                raise UserError(_(
                                    'La cantidad del producto "%s" (%s) no coincide con la cantidad del traslado previo (%s).'
                                ) % (move.product_id.display_name, move.quantity, prev_qty))
                
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

                    for move in picking.move_ids_without_package:
                        prev_move = previous_picking.move_ids_without_package.filtered(lambda m: m.product_id.id == move.product_id.id)
                        if prev_move:
                            prev_qty = sum(prev_move.mapped('quantity'))
                            if move.quantity != prev_qty:
                                raise UserError(_(
                                    'La cantidad del producto "%s" (%s) no coincide con la cantidad del traslado previo (%s).'
                                ) % (move.product_id.display_name, move.quantity, prev_qty))

        return super(StockPicking, self).button_validate()


class StockMove(models.Model):
    _inherit = "stock.move"

    requisition_order = fields.Char(
        string='Requisición', 
        readonly=True, 
        copy=False, 
        related='picking_id.requisition_order'
    )
    
    usage_origin = fields.Selection(
        related='picking_id.location_id.usage', 
        string='Uso de Ubicación Origen', 
        readonly=True
    )
    
    usage_dest = fields.Selection(
        related='picking_id.location_dest_id.usage', 
        string='Uso de Ubicación Destino', 
        readonly=True
    )

    user_can_edit_quantity = fields.Boolean(
        string="Puede editar cantidad",
        compute='_compute_user_can_edit_quantity',
        store=False
    )
    
    quantity_readonly = fields.Boolean(
        string="Cantidad solo lectura",
        compute='_compute_quantity_readonly',
        store=False
    )
    
    @api.depends_context('uid')
    def _compute_user_can_edit_quantity(self):
        group_id = "dv_requisition_custom.group_requisition_quantity_manager"
        has_group = self.env.user.has_group(group_id)
        for move in self:
            move.user_can_edit_quantity = has_group

    @api.depends('usage_origin', 'usage_dest', 'requisition_order', 'state')
    def _compute_quantity_readonly(self):
        for move in self:
            if (move.usage_origin == 'internal' and 
                move.usage_dest == 'transit' and 
                move.requisition_order and
                move.state not in ('done', 'cancel')):
                move.quantity_readonly = True
            else:
                move.quantity_readonly = False

    def write(self, vals):
        """
        BLOQUEO ABSOLUTO de modificación de cantidades en movimientos de requisición
        """
        # Verificar permisos
        group_id = "dv_requisition_custom.group_requisition_quantity_manager"
        has_group = self.env.user.has_group(group_id)
        
        # Lista de campos de cantidad que pueden modificarse
        quantity_fields = ['quantity', 'quantity_done', 'product_uom_qty', 'reserved_availability']
        
        # Verificar si se está intentando modificar algún campo de cantidad
        is_modifying_quantity = any(field in vals for field in quantity_fields)
        
        if not has_group and is_modifying_quantity:
            for move in self:
                # Solo aplicar a movimientos existentes de requisición origen
                if not move.id:
                    continue
                    
                if not (move.requisition_order and 
                        move.usage_origin == 'internal' and 
                        move.usage_dest == 'transit' and 
                        move.state not in ('done', 'cancel')):
                    continue
                
                # Obtener el valor actual y el nuevo valor
                current_qty = move.quantity_done if move.quantity_done else move.quantity
                
                # Determinar qué campo se está modificando
                new_qty = None
                if 'quantity_done' in vals:
                    new_qty = vals['quantity_done']
                elif 'quantity' in vals:
                    new_qty = vals['quantity']
                elif 'product_uom_qty' in vals:
                    # Si intentan cambiar la demanda, bloquear
                    if vals['product_uom_qty'] != move.product_uom_qty:
                        raise ValidationError(
                            _("⛔ BLOQUEADO - NO PUEDE MODIFICAR LA DEMANDA\n\n"
                              "Producto: %s\n"
                              "Demanda original: %s\n"
                              "Intento de cambiar a: %s\n\n"
                              "La demanda de movimientos de requisición no puede modificarse.") %
                            (move.product_id.display_name, move.product_uom_qty, vals['product_uom_qty'])
                        )
                
                # Validar la nueva cantidad
                if new_qty is not None:
                    # Solo permitir 0 o igual a product_uom_qty
                    if new_qty != 0 and new_qty != move.product_uom_qty:
                        raise ValidationError(
                            _("⛔ NO PUEDE MODIFICAR ESTA CANTIDAD\n\n"
                              "Producto: %s\n"
                              "Cantidad demandada: %s %s\n"
                              "Cantidad que intenta guardar: %s %s\n\n"
                              "✅ Solo se permite:\n"
                              "  • Cantidad = 0 (sin stock disponible)\n"
                              "  • Cantidad = %s (cantidad demandada)\n\n"
                              "❌ NO se permiten otros valores para evitar descuadres.") %
                            (move.product_id.display_name,
                             move.product_uom_qty,
                             move.product_uom.name,
                             new_qty,
                             move.product_uom.name,
                             move.product_uom_qty)
                        )
        
        # Si pasó todas las validaciones, ejecutar el write
        return super(StockMove, self).write(vals)