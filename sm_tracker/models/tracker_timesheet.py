# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class TrackerTimesheet(models.Model):
    _name = 'tracker.timesheet'
    _description = 'Registro de Tiempo'
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Descripción',
        required=True
    )
    
    task_id = fields.Many2one(
        'tracker.task',
        string='Tarea',
        required=True,
        ondelete='cascade'
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Empleado',
        required=True
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='Usuario',
        readonly=True
    )
    
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Tienda',
        required=True
    )
    
    date = fields.Date(
        string='Fecha',
        required=True,
        default=fields.Date.context_today
    )
    
    start_time = fields.Datetime(
        string='Hora Inicio'
    )
    
    end_time = fields.Datetime(
        string='Hora Fin'
    )
    
    hours = fields.Float(
        string='Horas',
        compute='_compute_hours',
        store=True
    )
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('running', 'En Progreso'),
        ('stopped', 'Detenido'),
    ], string='Estado', default='draft')
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company
    )
    
    @api.depends('start_time', 'end_time')
    def _compute_hours(self):
        for record in self:
            if record.start_time and record.end_time:
                delta = record.end_time - record.start_time
                record.hours = delta.total_seconds() / 3600.0
            else:
                record.hours = 0.0