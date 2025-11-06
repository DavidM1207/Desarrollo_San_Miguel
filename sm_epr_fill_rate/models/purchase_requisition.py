# -*- coding: utf-8 -*-

from odoo import models, api


class EmployeePurchaseRequisition(models.Model):
    _inherit = 'employee.purchase.requisition'

    @api.model
    def _generate_existing_fill_rate(self):
        """Genera registros de Fill Rate para todas las requisiciones existentes"""
        requisitions = self.search([])
        for requisition in requisitions:
            try:
                requisition._create_fill_rate_records()
            except Exception:
                # Si falla, continuar con la siguiente
                continue
        return True

    def action_generate_fill_rate(self):
        """Acción manual para generar/regenerar registros de fill rate"""
        for requisition in self:
            requisition._create_fill_rate_records()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Fill Rate',
                'message': 'Registros de Fill Rate generados correctamente',
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model_create_multi
    def create(self, vals_list):
        """Override create para generar registros de fill rate cuando se crea una requisición"""
        requisitions = super(PurchaseRequisition, self).create(vals_list)
        
        for requisition in requisitions:
            requisition._create_fill_rate_records()
        
        return requisitions

    def write(self, vals):
        """Override write para actualizar registros de fill rate cuando se modifican líneas"""
        res = super(PurchaseRequisition, self).write(vals)
        
        # Si se modifican las líneas de la requisición, actualizar fill rate
        if 'line_ids' in vals:
            for requisition in self:
                requisition._update_fill_rate_records()
        
        return res

    def _create_fill_rate_records(self):
        """Crea los registros de fill rate para cada producto en la requisición"""
        self.ensure_one()
        FillRate = self.env['purchase.requisition.fill.rate']
        
        for line in self.line_ids:
            if line.product_id:
                # Verificar si ya existe un registro
                existing = FillRate.search([
                    ('requisition_id', '=', self.id),
                    ('product_id', '=', line.product_id.id)
                ], limit=1)
                
                if not existing:
                    FillRate.create({
                        'requisition_id': self.id,
                        'product_id': line.product_id.id,
                        'demanda': line.product_qty,
                    })

    def _update_fill_rate_records(self):
        """Actualiza los registros de fill rate existentes"""
        self.ensure_one()
        FillRate = self.env['purchase.requisition.fill.rate']
        
        # Obtener todos los productos actuales en la requisición
        current_products = {}
        for line in self.line_ids:
            if line.product_id:
                if line.product_id.id not in current_products:
                    current_products[line.product_id.id] = 0.0
                current_products[line.product_id.id] += line.product_qty
        
        # Actualizar o crear registros de fill rate
        for product_id, qty in current_products.items():
            fill_rate = FillRate.search([
                ('requisition_id', '=', self.id),
                ('product_id', '=', product_id)
            ], limit=1)
            
            if fill_rate:
                fill_rate.write({'demanda': qty})
            else:
                FillRate.create({
                    'requisition_id': self.id,
                    'product_id': product_id,
                    'demanda': qty,
                })
        
        # Eliminar registros de productos que ya no están en la requisición
        existing_records = FillRate.search([('requisition_id', '=', self.id)])
        for record in existing_records:
            if record.product_id.id not in current_products:
                record.unlink()


class EmployeePurchaseRequisitionLine(models.Model):
    _inherit = 'employee.purchase.requisition.line'

    @api.model_create_multi
    def create(self, vals_list):
        """Override create para actualizar fill rate cuando se agregan líneas"""
        lines = super(PurchaseRequisitionLine, self).create(vals_list)
        
        # Agrupar por requisición para optimizar
        requisitions = lines.mapped('requisition_id')
        for requisition in requisitions:
            requisition._update_fill_rate_records()
        
        return lines

    def write(self, vals):
        """Override write para actualizar fill rate cuando se modifican líneas"""
        requisitions = self.mapped('requisition_id')
        res = super(PurchaseRequisitionLine, self).write(vals)
        
        # Si se modifica la cantidad o el producto, actualizar fill rate
        if 'product_qty' in vals or 'product_id' in vals:
            for requisition in requisitions:
                requisition._update_fill_rate_records()
        
        return res

    def unlink(self):
        """Override unlink para actualizar fill rate cuando se eliminan líneas"""
        requisitions = self.mapped('requisition_id')
        res = super(PurchaseRequisitionLine, self).unlink()
        
        for requisition in requisitions:
            requisition._update_fill_rate_records()
        
        return res