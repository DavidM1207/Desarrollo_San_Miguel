# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    tracker_analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        'hr_employee_analytic_account_rel',
        'employee_id',
        'analytic_account_id',
        string='Tiendas Asignadas',
        help='Cuentas analíticas (tiendas) a las que tiene acceso el empleado'
    )
    
    is_tracker_manager = fields.Boolean(
        string='Es Gerente Regional',
        help='Los gerentes regionales pueden ver múltiples tiendas'
    )
    
    tracker_task_ids = fields.One2many(
        'tracker.task',
        'employee_id',
        string='Tareas Asignadas'
    )
    
    tracker_task_count = fields.Integer(
        string='Total Tareas',
        compute='_compute_tracker_task_count'
    )
    
    tracker_timesheet_ids = fields.One2many(
        'tracker.timesheet',
        'employee_id',
        string='Registros de Tiempo'
    )
    
    tracker_total_hours = fields.Float(
        string='Horas Totales Tracker',
        compute='_compute_tracker_total_hours',
        help='Total de horas registradas en tracker'
    )
    
    @api.depends('tracker_task_ids')
    def _compute_tracker_task_count(self):
        for employee in self:
            employee.tracker_task_count = len(employee.tracker_task_ids)
    
    @api.depends('tracker_timesheet_ids.hours')
    def _compute_tracker_total_hours(self):
        for employee in self:
            employee.tracker_total_hours = sum(employee.tracker_timesheet_ids.mapped('hours'))
    
    def action_view_tracker_tasks(self):
        """Ver tareas asignadas al empleado"""
        self.ensure_one()
        return {
            'name': _('Tareas de %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'tracker.task',
            'view_mode': 'tree,form,kanban',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
    
    def action_view_tracker_timesheets(self):
        """Ver registros de tiempo del empleado"""
        self.ensure_one()
        return {
            'name': _('Registros de Tiempo de %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'tracker.timesheet',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }