# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class TrackerProject(models.Model):
    _name = 'tracker.project'
    _description = 'Proyecto de Servicios'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Número de Proyecto',
        required=True,
        copy=False,
        readonly=True,
        default='Nuevo'
    )
    
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Orden de Venta',
        readonly=True,
        copy=False
    )
    
    pos_order_id = fields.Many2one(
        'pos.order',
        string='Orden POS',
        readonly=True,
        copy=False
    )
    
    order_reference = fields.Char(
        string='Orden de Venta',
        compute='_compute_order_reference',
        store=True,
        readonly=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
        tracking=True
    )
    
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Tienda',
        required=True,
        tracking=True
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='Responsable',
        default=lambda self: self.env.user,
        tracking=True
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
        string='Número de Tareas',
        compute='_compute_task_count'
    )
    
    total_hours = fields.Float(
        string='Horas Totales',
        compute='_compute_total_hours',
        store=True
    )
    
    promise_date = fields.Date(
        string='Fecha Prometida',
        required=True,
        tracking=True
    )
    
    delivery_date = fields.Date(
        string='Fecha de Entrega',
        tracking=True
    )
    
    delay_days = fields.Integer(
        string='Días de Retraso',
        compute='_compute_delay_days',
        store=True
    )
    
    progress = fields.Float(
        string='Progreso',
        compute='_compute_progress',
        store=True
    )
    
    notes = fields.Text(string='Notas')
    
    invoice_ids = fields.Many2many(
        'account.move',
        string='Facturas',
        compute='_compute_invoice_ids',
        store=True
    )
    
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
    
    @api.depends('sale_order_id', 'pos_order_id')
    def _compute_order_reference(self):
        for record in self:
            if record.sale_order_id:
                record.order_reference = record.sale_order_id.name
            elif record.pos_order_id:
                record.order_reference = record.pos_order_id.pos_reference
            else:
                record.order_reference = False
    
    @api.depends('sale_order_id', 'pos_order_id')
    def _compute_invoice_ids(self):
        for record in self:
            if record.sale_order_id:
                record.invoice_ids = record.sale_order_id.invoice_ids
            elif record.pos_order_id:
                record.invoice_ids = record.pos_order_id.account_move
            else:
                record.invoice_ids = False
    
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
            if record.state == 'delivered' and record.delivery_date and record.promise_date:
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
            if not record.task_ids:
                record.progress = 0.0
            else:
                total_tasks = len(record.task_ids)
                done_tasks = len(record.task_ids.filtered(lambda t: t.state == 'done'))
                record.progress = (done_tasks / total_tasks) * 100 if total_tasks > 0 else 0.0
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'Nuevo') == 'Nuevo':
            vals['name'] = self.env['ir.sequence'].next_by_code('tracker.project') or 'Nuevo'
        return super(TrackerProject, self).create(vals)
    
    def write(self, vals):
        if 'state' in vals:
            vals['state_changed_by'] = self.env.user.id
            vals['state_changed_date'] = fields.Datetime.now()
        
        return super(TrackerProject, self).write(vals)
    
    def action_start_processing(self):
        for record in self:
            if record.state != 'pending':
                raise UserError(_('Solo se puede iniciar el procesamiento de proyectos pendientes.'))
            
            if not record.task_ids:
                raise UserError(_('El proyecto no tiene tareas asignadas.'))
            
            record.write({'state': 'processing'})
        return True
    
    def action_mark_delivered(self):
        for record in self:
            if record.state != 'processing':
                raise UserError(_('Solo se puede marcar como entregado un proyecto en proceso.'))
            
            pending_tasks = record.task_ids.filtered(lambda t: t.state not in ['done', 'cancel'])
            if pending_tasks:
                raise UserError(_('Todas las tareas deben estar terminadas antes de marcar el proyecto como entregado.'))
            
            record.write({
                'state': 'delivered',
                'delivery_date': fields.Date.today()
            })
        return True
    
    def action_view_tasks(self):
        self.ensure_one()
        return {
            'name': _('Tareas - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'tracker.task',
            'view_mode': 'tree,kanban,form',
            'domain': [('project_id', '=', self.id)],
            'context': {
                'default_project_id': self.id,
                'default_analytic_account_id': self.analytic_account_id.id,
            },
        }