# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class TrackerProject(models.Model):
    _name = 'tracker.project'
    _description = 'Proyecto Tracker'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Número de Proyecto',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('Nuevo')
    )
    
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Orden de Venta',
        readonly=True,
        ondelete='cascade'
    )
    
    pos_order_id = fields.Many2one(
        'pos.order',
        string='Orden de Punto de Venta',
        readonly=True,
        ondelete='cascade'
    )
    
    invoice_id = fields.Many2one(
        'account.move',
        string='Factura de Cliente',
        readonly=True,
        ondelete='cascade',
        domain=[('move_type', '=', 'out_invoice')]
    )
    
    order_reference = fields.Char(
        string='Referencia de Orden',
        compute='_compute_order_reference',
        store=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        compute='_compute_partner_id',
        store=True,
        readonly=True
    )
    
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Cuenta Analítica (Tienda)',
        required=True,
        readonly=True
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='Responsable',
        default=lambda self: self.env.user,
        tracking=True
    )
    
    date_start = fields.Datetime(
        string='Fecha de Inicio',
        default=fields.Datetime.now,
        readonly=True
    )
    
    date_end = fields.Datetime(
        string='Fecha de Finalización',
        readonly=True
    )
    
    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('in_progress', 'En Proceso'),
        ('delivered', 'Entregado'),
    ], string='Estado', default='pending', required=True, tracking=True)
    
    task_ids = fields.One2many(
        'tracker.task',
        'project_id',
        string='Tareas'
    )
    
    task_count = fields.Integer(
        string='Número de Tareas',
        compute='_compute_task_count'
    )
    
    total_hours = fields.Float(
        string='Total de Horas',
        compute='_compute_total_hours',
        store=True
    )
    
    notes = fields.Text(string='Notas')
    
    @api.depends('sale_order_id', 'pos_order_id', 'invoice_id')
    def _compute_order_reference(self):
        """Obtener referencia de la orden (venta, POS o factura)"""
        for project in self:
            if project.sale_order_id:
                project.order_reference = project.sale_order_id.name
            elif project.pos_order_id:
                project.order_reference = project.pos_order_id.name
            elif project.invoice_id:
                project.order_reference = project.invoice_id.name
            else:
                project.order_reference = False
    
    @api.depends('sale_order_id', 'pos_order_id', 'invoice_id')
    def _compute_partner_id(self):
        """Obtener cliente de la orden (venta, POS o factura)"""
        for project in self:
            if project.sale_order_id:
                project.partner_id = project.sale_order_id.partner_id
            elif project.pos_order_id:
                project.partner_id = project.pos_order_id.partner_id
            elif project.invoice_id:
                project.partner_id = project.invoice_id.partner_id
            else:
                project.partner_id = False
    
    @api.depends('task_ids')
    def _compute_task_count(self):
        for project in self:
            project.task_count = len(project.task_ids)
    
    @api.depends('task_ids.total_hours')
    def _compute_total_hours(self):
        for project in self:
            project.total_hours = sum(project.task_ids.mapped('total_hours'))
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                vals['name'] = self.env['ir.sequence'].next_by_code('tracker.project') or _('Nuevo')
        return super(TrackerProject, self).create(vals_list)
    
    def action_view_tasks(self):
        """Acción para ver las tareas del proyecto"""
        self.ensure_one()
        return {
            'name': _('Tareas del Proyecto'),
            'type': 'ir.actions.act_window',
            'res_model': 'tracker.task',
            'view_mode': 'tree,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id}
        }
    
    def action_set_pending(self):
        """Cambiar estado a Pendiente"""
        self.write({'state': 'pending'})
    
    def action_set_in_progress(self):
        """Cambiar estado a En Proceso"""
        self.write({'state': 'in_progress'})
    
    def action_set_delivered(self):
        """Cambiar estado a Entregado"""
        # Verificar que todas las tareas estén completadas
        pending_tasks = self.task_ids.filtered(lambda t: t.state != 'done')
        if pending_tasks:
            raise UserError(_(
                'No se puede marcar el proyecto como entregado. '
                'Las siguientes tareas aún no están completadas:\n%s'
            ) % '\n'.join(pending_tasks.mapped('name')))
        
        self.write({
            'state': 'delivered',
            'date_end': fields.Datetime.now()
        })