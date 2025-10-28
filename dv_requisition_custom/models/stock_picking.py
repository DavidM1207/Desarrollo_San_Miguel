# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError

class StockPicking(models.Model):
    _inherit= "stock.picking"

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

    requisition_order = fields.Char(string='Requisición', readonly=True, copy=False, related='picking_id.requisition_order')
    usage_origin = fields.Selection(related='picking_id.location_id.usage', string='Uso de Ubicación Origen', readonly=True)
    usage_dest = fields.Selection(related='picking_id.location_dest_id.usage', string='Uso de Ubicación Destino', readonly=True)

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
        """
        Hace el campo quantity de solo lectura cuando:
        - Es un movimiento de internal a transit
        - Tiene requisition_order
        - El estado no es 'done' o 'cancel'
        """
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
        BLOQUEO CRÍTICO: Prevenir cualquier modificación de quantity 
        en movimientos de requisición internal->transit
        """
        # Si se intenta modificar 'quantity' o 'quantity_done'
        if 'quantity' in vals or 'quantity_done' in vals:
            # Verificar permisos del usuario
            group_id = "dv_requisition_custom.group_requisition_quantity_manager"
            has_group = self.env.user.has_group(group_id)
            
            # Si no tiene permisos especiales, validar cada movimiento
            if not has_group:
                for move in self:
                    # Solo aplicar restricción a movimientos de requisición internal->transit
                    if (move.requisition_order and 
                        move.usage_origin == 'internal' and 
                        move.usage_dest == 'transit' and 
                        move.state not in ('done', 'cancel')):
                        
                        # Obtener la cantidad que se intenta guardar
                        new_quantity = vals.get('quantity', vals.get('quantity_done', move.quantity))
                        
                        # Si es diferente a la demanda, bloquear
                        if new_quantity != move.product_uom_qty:
                            raise UserError(
                                _("⛔ NO PUEDE MODIFICAR LA CANTIDAD\n\n"
                                  "Este movimiento es parte de una requisición y la cantidad "
                                  "está bloqueada para mantener la sincronización.\n\n"
                                  "📦 Producto: %s\n"
                                  "✅ Cantidad requerida: %s %s\n"
                                  "❌ Cantidad que intenta guardar: %s %s\n\n"
                                  "💡 La cantidad realizada debe ser igual a la demandada.") %
                                (move.product_id.display_name,
                                 move.product_uom_qty,
                                 move.product_uom.name,
                                 new_quantity,
                                 move.product_uom.name)
                            )
        
        return super(StockMove, self).write(vals)

    @api.constrains('quantity', 'product_uom_qty')
    def _check_quantity_constraints(self):
        """
        Validación adicional como segunda capa de seguridad
        """
        group_id = "dv_requisition_custom.group_requisition_quantity_manager"
        has_group = self.env.user.has_group(group_id)
        
        if not has_group:
            for move in self:
                if (move.requisition_order and 
                    move.usage_origin == 'internal' and 
                    move.usage_dest == 'transit' and 
                    move.state not in ('done', 'cancel')):
                    
                    if move.quantity != move.product_uom_qty:
                        raise ValidationError(
                            _("⚠️ Validación de integridad: La cantidad del producto '%s' "
                              "debe ser %s (detectado %s).") %
                            (move.product_id.display_name, 
                             move.product_uom_qty,
                             move.quantity)
                        )