# tracker/models/sale_order.py
# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    tracker_project_ids = fields.One2many(
        'tracker.project',
        'sale_order_id',
        string='Proyectos Tracker'
    )
    
    tracker_project_count = fields.Integer(
        string='Trackers',
        compute='_compute_tracker_project_count'
    )
    
    has_service_products = fields.Boolean(
        string='Tiene Servicios',
        compute='_compute_has_service_products',
        help='Indica si la orden tiene productos de servicio en líneas o BoMs'
    )
    
    @api.depends('tracker_project_ids')
    def _compute_tracker_project_count(self):
        for order in self:
            order.tracker_project_count = len(order.tracker_project_ids)
    
    @api.depends('order_line.product_id')
    def _compute_has_service_products(self):
        for order in self:
            has_service = False
            for line in order.order_line:
                if line.product_id and line.product_id.type == 'service':
                    has_service = True
                    break
                
                if line.product_id:
                    bom = self.env['mrp.bom'].search([
                        ('product_tmpl_id', '=', line.product_id.product_tmpl_id.id)
                    ], limit=1)
                    
                    if bom:
                        service_components = bom.bom_line_ids.filtered(
                            lambda l: l.product_id.type == 'service'
                        )
                        if service_components:
                            has_service = True
                            break
            
            order.has_service_products = has_service
    
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        
        for order in self:
            if order.has_service_products and not order.tracker_project_ids:
                order._auto_create_tracker_project()
        
        return res
    
    def _auto_create_tracker_project(self):
        self.ensure_one()
        
        analytic_account = False
        if self.analytic_account_id:
            analytic_account = self.analytic_account_id
        else:
            for line in self.order_line:
                if line.analytic_distribution:
                    account_ids = [int(k) for k in line.analytic_distribution.keys()]
                    if account_ids:
                        analytic_account = self.env['account.analytic.account'].browse(account_ids[0])
                        break
        
        if not analytic_account:
            return False
        
        project_vals = {
            'sale_order_id': self.id,
            'partner_id': self.partner_id.id,
            'analytic_account_id': analytic_account.id,
            'promise_date': self.commitment_date or self.date_order.date(),
            'user_id': self.user_id.id,
        }
        
        project = self.env['tracker.project'].create(project_vals)
        
        service_products = project._get_service_products_from_sale()
        
        if service_products:
            task_obj = self.env['tracker.task']
            for product, qty in service_products.items():
                task_vals = {
                    'project_id': project.id,
                    'product_id': product.id,
                    'name': product.name,
                    'analytic_account_id': analytic_account.id,
                }
                task_obj.create(task_vals)
        
        return project
    
    def action_view_tracker_projects(self):
        self.ensure_one()
        return {
            'name': _('Proyectos Tracker'),
            'type': 'ir.actions.act_window',
            'res_model': 'tracker.project',
            'view_mode': 'tree,form,kanban',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {'default_sale_order_id': self.id},
        }