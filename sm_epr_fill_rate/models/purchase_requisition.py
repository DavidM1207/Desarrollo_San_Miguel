# -*- coding: utf-8 -*-
from odoo import models, api


class EmployeePurchaseRequisition(models.Model):
    _inherit = 'employee.purchase.requisition'

    @api.model_create_multi
    def create(self, vals_list):
        requisitions = super(EmployeePurchaseRequisition, self).create(vals_list)
        for requisition in requisitions:
            try:
                requisition._create_fill_rate_records()
            except:
                pass
        return requisitions

    def write(self, vals):
        res = super(EmployeePurchaseRequisition, self).write(vals)
        if 'line_ids' in vals:
            for requisition in self:
                try:
                    requisition._update_fill_rate_records()
                except:
                    pass
        return res

    def _create_fill_rate_records(self):
        self.ensure_one()
        FillRate = self.env['purchase.requisition.fill.rate']
        
        for line in self.line_ids:
            if line.product_id:
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
        self.ensure_one()
        FillRate = self.env['purchase.requisition.fill.rate']
        
        current_products = {}
        for line in self.line_ids:
            if line.product_id:
                if line.product_id.id not in current_products:
                    current_products[line.product_id.id] = 0.0
                current_products[line.product_id.id] += line.product_qty
        
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
        
        existing_records = FillRate.search([('requisition_id', '=', self.id)])
        for record in existing_records:
            if record.product_id.id not in current_products:
                record.unlink()


class EmployeePurchaseRequisitionLine(models.Model):
    _inherit = 'employee.purchase.requisition.line'

    @api.model_create_multi
    def create(self, vals_list):
        lines = super(EmployeePurchaseRequisitionLine, self).create(vals_list)
        requisitions = lines.mapped('requisition_id')
        for requisition in requisitions:
            try:
                requisition._update_fill_rate_records()
            except:
                pass
        return lines

    def write(self, vals):
        requisitions = self.mapped('requisition_id')
        res = super(EmployeePurchaseRequisitionLine, self).write(vals)
        if 'product_qty' in vals or 'product_id' in vals:
            for requisition in requisitions:
                try:
                    requisition._update_fill_rate_records()
                except:
                    pass
        return res

    def unlink(self):
        requisitions = self.mapped('requisition_id')
        res = super(EmployeePurchaseRequisitionLine, self).unlink()
        for requisition in requisitions:
            try:
                requisition._update_fill_rate_records()
            except:
                pass
        return res