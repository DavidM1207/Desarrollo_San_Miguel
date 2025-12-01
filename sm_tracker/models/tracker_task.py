# tracker/models/tracker_task.py
# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class TrackerTask(models.Model):
    _name = 'tracker.task'
    _description = 'Tarea de Servicio'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, id'

    name = fields.Char(
        string='Descripción',
        required=True,
        tracking=True
    )
    
    sequence = fields.Integer(string='Secuencia', default=10)
    
    project_id = fields.Many2one(
        'tracker.project',
        string='Proyecto',
        required=True,
        ondelete='cascade',
        tracking=True
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Servicio',
        required=True,
        domain=[('type', '=', 'service')],
        tracking=True,
        readonly=True
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Operario Asignado',
        tracking=True,
        help='Empleado responsable de ejecutar esta tarea'
    )
    
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Tienda',
        required=True,
        tracking=True
    )
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('ready', 'Listo'),
        ('in_progress', 'En Progreso'),
        ('done', 'Terminado'),
        ('cancel', 'Cancelado'),
    ], string='Estado', default='draft', required=True, tracking=True)
    
    timesheet_ids = fields.One2many(
        'tracker.timesheet',
        'task_id',
        string='Registro de Tiempos'
    )
    
    total_hours = fields.Float(
        string='Horas Totales',
        compute='_compute_total_hours',
        store=True,
        help='Total de horas trabajadas en esta tarea'
    )
    
    planned_hours = fields.Float(
        string='Horas Planificadas',
        help='Horas estimadas para completar la tarea'
    )
    
    notes = fields.Text(string='Notas')
    
    promise_date = fields.Date(
        related='project_id.promise_date',
        string='Fecha Prometida',
        store=True,
        readonly=True
    )
    
    partner_id = fields.Many2one(
        related='project_id.partner_id',
        string='Cliente',
        store=True,
        readonly=True
    )
    
    project_state = fields.Selection(
        related='project_id.state',
        string='Estado Proyecto',
        store=True,
        readonly=True
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
    
    @api.depends('timesheet_ids.hours')
    def _compute_total_hours(self):
        for record in self:
            record.total_hours = sum(record.timesheet_ids.mapped('hours'))
    
    def write(self, vals):
        if 'state' in vals:
            vals['state_changed_by'] = self.env.user.id
            vals['state_changed_date'] = fields.Datetime.now()
        
        return super(TrackerTask, self).write(vals)
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.name
    
    def action_start_task(self):
        for record in self:
            if record.state not in ['ready', 'draft']:
                raise UserError(_('Solo se puede iniciar una tarea en estado Listo o Borrador.'))
            
            if not record.employee_id:
                raise UserError(_('Debe asignar un operario antes de iniciar la tarea.'))
            
            record.write({'state': 'in_progress'})
            
            if record.project_id.state == 'pending':
                record.project_id.write({'state': 'processing'})
        
        return True
    
    def action_complete_task(self):
        for record in self:
            if record.state != 'in_progress':
                raise UserError(_('Solo se puede completar una tarea en progreso.'))
            
            record.write({'state': 'done'})
        
        return True
    
    def action_cancel_task(self):
        for record in self:
            if record.state == 'done':
                raise UserError(_('No se puede cancelar una tarea terminada.'))
            record.write({'state': 'cancel'})
        return True
    
    def action_reset_to_draft(self):
        for record in self:
            record.write({'state': 'draft'})
        return True
    
    def action_view_timesheets(self):
        self.ensure_one()
        return {
            'name': _('Registros de Tiempo - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'tracker.timesheet',
            'view_mode': 'tree,form',
            'domain': [('task_id', '=', self.id)],
            'context': {
                'default_task_id': self.id,
                'default_employee_id': self.employee_id.id,
                'default_analytic_account_id': self.analytic_account_id.id,
            },
        }