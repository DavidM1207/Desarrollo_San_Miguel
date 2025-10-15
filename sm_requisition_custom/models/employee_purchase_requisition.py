# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class EmployeePurchaseRequisition(models.Model):
    _inherit = "employee.purchase.requisition"

    def create(self, vals):
        # Saltar validaciones si está en contexto de importación
        if self.env.context.get('import_file') or self.env.context.get('skip_requisition_validations'):
            return super(EmployeePurchaseRequisition, self).create(vals)
        
        has_purchase_order = any(
            line[2].get('requisition_type') == 'purchase_order' 
            for line in vals.get('requisition_order_ids', []) 
            if len(line) > 2 and isinstance(line[2], dict)
        )
        
        if not has_purchase_order:
            has_purchase_order = any(
                line.requisition_type == 'purchase_order'
                for record in self
                for line in record.requisition_order_ids
            )
        
        # Validación mejorada para evitar errores en importación
        has_sale_ok = False
        bad_product_names = []
        
        for cmd in vals.get('requisition_order_ids', []):
            if len(cmd) > 2 and isinstance(cmd[2], dict):
                data = cmd[2]
                pid = data.get('product_id')
                if pid:
                    try:
                        product = self.env['product.product'].browse(pid)
                        if product.exists() and not product.sale_ok:
                            has_sale_ok = True
                            bad_product_names.append(product.display_name)
                    except Exception:
                        # Si hay error al obtener el producto, continuar
                        continue

        if has_purchase_order and not self.env.user.has_group('dv_requisition_custom.group_requisition_create_req_manager2'):
            raise UserError(_('No tiene permiso para modificar la requisición de compra.'))

        if has_sale_ok and self.env.user.has_group('dv_requisition_custom.group_requisition_create_req_manager2') and has_purchase_order:
            max_show = 20
            shown = bad_product_names[:max_show]
            extra = len(bad_product_names) - max_show
            suffix = _('\n…y %s más.') % extra if extra > 0 else ''
            raise UserError(
                _('No es posible guardar requisición de compra: '
                  'los siguientes productos no están marcados como de venta:\n- %s%s'
                ) % ('\n- '.join(shown), suffix)
            )
        
        return super(EmployeePurchaseRequisition, self).create(vals)

    def write(self, vals):
        # Saltar validaciones si está en contexto de importación
        if self.env.context.get('import_file') or self.env.context.get('skip_requisition_validations'):
            return super(EmployeePurchaseRequisition, self).write(vals)
        
        has_purchase_order = any(
            line[2].get('requisition_type') == 'purchase_order' 
            for line in vals.get('requisition_order_ids', []) 
            if len(line) > 2 and isinstance(line[2], dict)
        )
        
        if not has_purchase_order:
            has_purchase_order = any(
                line.requisition_type == 'purchase_order'
                for record in self
                for line in record.requisition_order_ids
            )
        
        # Validación mejorada para evitar errores en importación
        has_sale_ok = False
        bad_product_names = []
        
        for cmd in vals.get('requisition_order_ids', []):
            if len(cmd) > 2 and isinstance(cmd[2], dict):
                data = cmd[2]
                pid = data.get('product_id')
                if pid:
                    try:
                        product = self.env['product.product'].browse(pid)
                        if product.exists() and not product.sale_ok:
                            has_sale_ok = True
                            bad_product_names.append(product.display_name)
                    except Exception:
                        # Si hay error al obtener el producto, continuar
                        continue

        if has_purchase_order and not self.env.user.has_group('dv_requisition_custom.group_requisition_create_req_manager2'):
            raise UserError(_('No tiene permiso para modificar la requisición de compra.'))

        if has_sale_ok and self.env.user.has_group('dv_requisition_custom.group_requisition_create_req_manager2') and has_purchase_order:
            max_show = 20
            shown = bad_product_names[:max_show]
            extra = len(bad_product_names) - max_show
            suffix = _('\n…y %s más.') % extra if extra > 0 else ''
            raise UserError(
                _('No es posible guardar requisición de compra: '
                  'los siguientes productos no están marcados como de venta:\n- %s%s'
                ) % ('\n- '.join(shown), suffix)
            )
        
        return super(EmployeePurchaseRequisition, self).write(vals)