# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class TrackerTask(models.Model):
    _name = 'tracker.task'
    _description = 'Tarea Tracker'
    _order = 'id desc'

    name = fields.Char(
        string='Descripción',
        required=True
    )
    
    project_id = fields.Many2one(
        'tracker.project',
        string='Proyecto',
        required=True,
        ondelete='cascade'
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Servicio',
        required=True,
        readonly=True
    )
    
    quantity = fields.Float(
        string='Cantidad',
        default=1.0,
        readonly=True
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Operario'
    )
    
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Tienda',
        required=True
    )
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('ready', 'Listo'),
        ('in_progress', 'En Progreso'),
        ('paused', 'Pausado'),
        ('done', 'Terminado'),
        ('cancel', 'Cancelado'),
    ], string='Estado', default='draft', required=True)
    
    timesheet_ids = fields.One2many(
        'tracker.timesheet',
        'task_id',
        string='Registros de Tiempo'
    )
    
    total_hours = fields.Float(
        string='Horas Totales',
        compute='_compute_total_hours',
        store=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company
    )
    
    @api.depends('timesheet_ids.hours')
    def _compute_total_hours(self):
        for record in self:
            record.total_hours = sum(record.timesheet_ids.mapped('hours'))
    
    def action_start_task(self):
        for record in self:
            if not record.employee_id:
                raise UserError(_('Debe asignar un operario antes de iniciar la tarea.'))
            
            timesheet_vals = {
                'task_id': record.id,
                'employee_id': record.employee_id.id,
                'analytic_account_id': record.analytic_account_id.id,
                'name': record.name,
                'date': fields.Date.today(),
                'start_time': fields.Datetime.now(),
                'state': 'running',
                'user_id': self.env.user.id
            }
            self.env['tracker.timesheet'].create(timesheet_vals)
            record.write({'state': 'in_progress'})
        
        return True
    
    def action_pause_task(self):
        for record in self:
            running_timesheet = record.timesheet_ids.filtered(lambda t: t.state == 'running')
            if running_timesheet:
                running_timesheet.write({
                    'end_time': fields.Datetime.now(),
                    'state': 'stopped'
                })
            record.write({'state': 'paused'})
        return True
    
    def action_complete_task(self):
        for record in self:
            running_timesheet = record.timesheet_ids.filtered(lambda t: t.state == 'running')
            if running_timesheet:
                running_timesheet.write({
                    'end_time': fields.Datetime.now(),
                    'state': 'stopped'
                })
            record.write({'state': 'done'})
        return True