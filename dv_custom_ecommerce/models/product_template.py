from odoo import models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_additionnal_combination_info(self, product_or_template, quantity, date, website):
        res = super()._get_additionnal_combination_info(product_or_template, quantity, date, website)
        
        if product_or_template._name == 'product.template':
            product = product_or_template.product_variant_ids[:1] if product_or_template.product_variant_ids else product_or_template
        else:
            product = product_or_template
        
        total_stock = 0
        if product and product._name == 'product.product':
            if website.sudo().website_warehouses_ids:
                warehouse_locations = website.sudo().website_warehouses_ids.mapped('lot_stock_id')
                quants = self.env['stock.quant'].sudo().search([
                    ('product_id', '=', product.id),
                    ('location_id', 'child_of', warehouse_locations.ids)
                ])
            else:
                quants = self.env['stock.quant'].sudo().search([
                    ('product_id', '=', product.id),
                    ('location_id.usage', '=', 'internal')
                ])
            total_stock = sum(max(0, quant.quantity - quant.reserved_quantity) for quant in quants)

        res.update({
            'total_stock_all_warehouses': total_stock,
            'is_out_of_stock': total_stock <= 0
        })
        return res
