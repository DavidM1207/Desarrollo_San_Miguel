# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class TrackerProject(models.Model):
    _name = 'tracker.project'
    _description = 'Proyecto de Seguimiento'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'promise_date desc, id desc'

    name = fields.Char(
        string='Referencia',
        required=True,
        copy=False,
        readonly=True,
        default='Nuevo',
        tracking=True
    )
    
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Orden de Venta',
        tracking=True,
        readonly=True,
        help='Orden de venta origen del proyecto'
    )
    
    invoice_ids = fields.Many2many(
        'account.move',
        'tracker_project_invoice_rel',
        'project_id',
        'invoice_id',
        string='Facturas',
        domain=[('move_type', '=', 'out_invoice')],
        tracking=True
    )
    
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Tienda',
        required=True,
        tracking=True,
        help='Cuenta analítica de la tienda donde se genera el proyecto'
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
        tracking=True,
        readonly=True
    )
    
    promise_date = fields.Date(
        string='Fecha Prometida',
        required=True,
        tracking=True,
        help='Fecha en que se prometió la entrega al cliente'
    )
    
    delivery_date = fields.Date(
        string='Fecha de Entrega',
        tracking=True,
        readonly=True,
        help='Fecha real de entrega del proyecto'
    )
    
    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('processing', 'Procesando'),
        ('delivered', 'Entregado'),
    ], string='Estado', default='pending', required=True, tracking=True)
    
    task_ids = fields.One2many(
        'tracker.task',
        'project_id',
        string='Tareas de Servicio'
    )
    
    task_count = fields.Integer(
        string='Total Tareas',
        compute='_compute_task_count',
        store=True
    )
    
    total_hours = fields.Float(
        string='Horas Totales',
        compute='_compute_total_hours',
        store=True,
        help='Total de horas trabajadas en todas las tareas'
    )
    
    delay_days = fields.Integer(
        string='Días de Retraso',
        compute='_compute_delay_days',
        store=True,
        help='Días de diferencia entre fecha prometida y entregada'
    )
    
    progress = fields.Float(
        string='Progreso (%)',
        compute='_compute_progress',
        store=True
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='Responsable',
        default=lambda self: self.env.user,
        tracking=True
    )
    
    notes = fields.Text(string='Notas')
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company
    )
    
    state_changed_by = fields.Many2one(
        'res.users',
        string='Estado Cambiado Por',
        readonly=True
    )
    
    state_changed_date = fields.Datetime(
        string='Fecha Cambio Estado',
        readonly=True
    )
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'Nuevo') == 'Nuevo':
            vals['name'] = self.env['ir.sequence'].next_by_code('tracker.project') or 'Nuevo'
        return super(TrackerProject, self).create(vals)
    
    @api.depends('task_ids')
    def _compute_task_count(self):
        for record in self:
            record.task_count = len(record.task_ids)
    
    @api.depends('task_ids.total_hours')
    def _compute_total_hours(self):
        for record in self:
            record.total_hours = sum(record.task_ids.mapped('total_hours'))
    
    @api.depends('promise_date', 'delivery_date', 'state')
    def _compute_delay_days(self):
        for record in self:
            if record.state == 'delivered' and record.promise_date and record.delivery_date:
                delta = record.delivery_date - record.promise_date
                record.delay_days = delta.days
            elif record.state != 'delivered' and record.promise_date:
                today = fields.Date.today()
                if today > record.promise_date:
                    delta = today - record.promise_date
                    record.delay_days = delta.days
                else:
                    record.delay_days = 0
            else:
                record.delay_days = 0
    
    @api.depends('task_ids.state')
    def _compute_progress(self):
        for record in self:
            if record.task_ids:
                total_tasks = len(record.task_ids)
                completed_tasks = len(record.task_ids.filtered(lambda t: t.state == 'done'))
                record.progress = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
            else:
                record.progress = 0
    
    def write(self, vals):
        if 'state' in vals:
            vals['state_changed_by'] = self.env.user.id
            vals['state_changed_date'] = fields.Datetime.now()
            
            if vals['state'] == 'delivered' and not self.delivery_date:
                vals['delivery_date'] = fields.Date.today()
        
        return super(TrackerProject, self).write(vals)
    
    def action_start_processing(self):
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_('Solo se puede procesar un proyecto pendiente.'))
        self.write({'state': 'processing'})
        return True
    
    def action_mark_delivered(self):
        self.ensure_one()
        if self.state != 'processing':
            raise UserError(_('Solo se puede entregar un proyecto en procesamiento.'))
        
        pending_tasks = self.task_ids.filtered(lambda t: t.state != 'done')
        if pending_tasks:
            raise UserError(_(
                'No se puede marcar como entregado. '
                'Aún hay %d tarea(s) pendiente(s).'
            ) % len(pending_tasks))
        
        self.write({
            'state': 'delivered',
            'delivery_date': fields.Date.today()
        })
        return True
    
    def action_view_tasks(self):
        self.ensure_one()
        return {
            'name': _('Tareas de %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'tracker.task',
            'view_mode': 'tree,form,kanban',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }