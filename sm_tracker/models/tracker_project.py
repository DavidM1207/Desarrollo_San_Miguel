# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class TrackerProject(models.Model):
    _name = 'tracker.project'
    _description = 'Proyecto Tracker'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Número',
        required=True,
        copy=False,
        readonly=True,
        default='Nuevo'
    )
    
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Orden de Venta',
        readonly=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True
    )
    
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Tienda',
        required=True
    )
    
    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('processing', 'En Proceso'),
        ('delivered', 'Entregado'),
    ], string='Estado', default='pending', required=True, tracking=True)
    
    task_ids = fields.One2many(
        'tracker.task',
        'project_id',
        string='Tareas'
    )
    
    task_count = fields.Integer(
        string='Tareas',
        compute='_compute_task_count'
    )
    
    promise_date = fields.Date(
        string='Fecha Prometida',
        required=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company
    )
    
    @api.depends('task_ids')
    def _compute_task_count(self):
        for record in self:
            record.task_count = len(record.task_ids)
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'Nuevo') == 'Nuevo':
            vals['name'] = self.env['ir.sequence'].next_by_code('tracker.project') or 'Nuevo'
        return super(TrackerProject, self).create(vals)
    
    def action_view_tasks(self):
        self.ensure_one()
        return {
            'name': _('Tareas'),
            'type': 'ir.actions.act_window',
            'res_model': 'tracker.task',
            'view_mode': 'tree,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }