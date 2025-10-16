
# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class EmployeePurchaseRequisition(models.Model):
    _inherit= "employee.purchase.requisition"

    def create(self, vals):
        has_purchase_order = any(
             line[2].get('requisition_type') == 'purchase_order' 
             for line in vals.get('requisition_order_ids', []) 
             if len(line) > 2 and isinstance(line[2], dict)
         )
        #print("///////////////////////////////////////has_purchase_order1", has_purchase_order)
        if not has_purchase_order:
            has_purchase_order = any(
                line.requisition_type == 'purchase_order'
                for record in self
                for line in record.requisition_order_ids
            )
            #print("///////////////////////////////////////has_purchase_order2", has_purchase_order)
        has_sale_ok = any(
            not self.env['product.product'].browse(line[2].get('product_id')).sale_ok
            for line in vals.get('requisition_order_ids', []) 
            if len(line) > 2 and isinstance(line[2], dict) and line[2].get('product_id')
        )   

        #print("///////////////////////////////////////has_purchase_order3", has_purchase_order)
        if has_purchase_order and not self.env.user.has_group('dv_requisition_custom.group_requisition_create_req_manager2'):
            raise UserError(_('No tiene permiso para modificar la requisición de compra.'))
        
        bad_product_names = []
        for cmd in vals.get('requisition_order_ids', []):
            if len(cmd) > 2 and isinstance(cmd[2], dict):
                data = cmd[2]
                pid = data.get('product_id')
                if pid:
                    product = self.env['product.product'].browse(pid)
                    if not product.sale_ok:
                        bad_product_names.append(product.display_name)

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
        has_purchase_order = any(
             line[2].get('requisition_type') == 'purchase_order' 
             for line in vals.get('requisition_order_ids', []) 
             if len(line) > 2 and isinstance(line[2], dict)
         )
        #print("///////////////////////////////////////has_purchase_order1", has_purchase_order)
        if not has_purchase_order:
            has_purchase_order = any(
                line.requisition_type == 'purchase_order'
                for record in self
                for line in record.requisition_order_ids
            )
            #print("///////////////////////////////////////has_purchase_order2", has_purchase_order)
        has_sale_ok = any(
            not self.env['product.product'].browse(line[2].get('product_id')).sale_ok
            for line in vals.get('requisition_order_ids', []) 
            if len(line) > 2 and isinstance(line[2], dict) and line[2].get('product_id')
        )
        #print("///////////////////////////////////////has_purchase_order3", has_purchase_order)
        if has_purchase_order and not self.env.user.has_group('dv_requisition_custom.group_requisition_create_req_manager2'):
            raise UserError(_('No tiene permiso para modificar la requisición de compra.'))

        bad_product_names = []
        for cmd in vals.get('requisition_order_ids', []):
            if len(cmd) > 2 and isinstance(cmd[2], dict):
                data = cmd[2]
                pid = data.get('product_id')
                if pid:
                    product = self.env['product.product'].browse(pid)
                    if not product.sale_ok:
                        bad_product_names.append(product.display_name)

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


