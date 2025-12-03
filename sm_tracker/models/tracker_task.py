# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class TrackerTask(models.Model):
    _name = 'tracker.task'
    _description = 'Tarea de Servicio'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id'

    name = fields.Char(
        string='Descripción',
        required=True,
        tracking=True
    )
    
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
    
    quantity = fields.Float(
        string='Cantidad',
        default=1.0,
        tracking=True,
        readonly=True,
        help='Cantidad de servicios a realizar'
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
        ('paused', 'Pausado'),
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
    
    active_timesheet_id = fields.Many2one(
        'tracker.timesheet',
        string='Registro Activo',
        help='Registro de tiempo actualmente en progreso'
    )
    
    current_start_time = fields.Datetime(
        string='Inicio Actual',
        help='Hora de inicio del registro actual'
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
            if record.state not in ['ready', 'draft', 'paused']:
                raise UserError(_('Solo se puede iniciar una tarea en estado Listo, Borrador o Pausado.'))
            
            if not record.employee_id:
                raise UserError(_('Debe asignar un operario antes de iniciar la tarea.'))
            
            current_time = fields.Datetime.now()
            
            timesheet_vals = {
                'task_id': record.id,
                'employee_id': record.employee_id.id,
                'analytic_account_id': record.analytic_account_id.id,
                'name': record.name,
                'date': fields.Date.today(),
                'start_time': current_time,
                'state': 'running',
                'user_id': self.env.user.id
            }
            timesheet = self.env['tracker.timesheet'].create(timesheet_vals)
            
            record.write({
                'state': 'in_progress',
                'active_timesheet_id': timesheet.id,
                'current_start_time': current_time
            })
            
            if record.project_id.state == 'pending':
                record.project_id.write({'state': 'processing'})
        
        return True
    
    def action_pause_task(self):
        for record in self:
            if record.state != 'in_progress':
                raise UserError(_('Solo se puede pausar una tarea en progreso.'))
            
            if record.active_timesheet_id:
                record.active_timesheet_id.write({
                    'end_time': fields.Datetime.now(),
                    'state': 'stopped',
                    'user_id': self.env.user.id
                })
            
            record.write({
                'state': 'paused',
                'active_timesheet_id': False,
                'current_start_time': False
            })
        
        return True
    
    def action_complete_task(self):
        for record in self:
            if record.state not in ['in_progress', 'paused']:
                raise UserError(_('Solo se puede completar una tarea en progreso o pausada.'))
            
            if record.active_timesheet_id:
                record.active_timesheet_id.write({
                    'end_time': fields.Datetime.now(),
                    'state': 'stopped',
                    'user_id': self.env.user.id
                })
            
            record.write({
                'state': 'done',
                'active_timesheet_id': False,
                'current_start_time': False
            })
        
        return True
    
    def action_cancel_task(self):
        for record in self:
            if record.state == 'done':
                raise UserError(_('No se puede cancelar una tarea terminada.'))
            
            if record.active_timesheet_id:
                record.active_timesheet_id.write({
                    'end_time': fields.Datetime.now(),
                    'state': 'stopped'
                })
            
            record.write({
                'state': 'cancel',
                'active_timesheet_id': False,
                'current_start_time': False
            })
        return True
    
    def action_reset_to_draft(self):
        for record in self:
            record.write({
                'state': 'draft',
                'current_start_time': False
            })
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