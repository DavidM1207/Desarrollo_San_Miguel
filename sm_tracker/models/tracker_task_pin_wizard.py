# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class TrackerTaskPinWizard(models.TransientModel):
    _name = 'tracker.task.pin.wizard'
    _description = 'Wizard para validar NIP al iniciar tarea'

    task_id = fields.Many2one(
        'tracker.task',
        string='Tarea',
        required=True,
        readonly=True
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Operario',
        related='task_id.employee_id',
        readonly=True
    )
    
    pin = fields.Char(
        string='NIP del Operario',
        required=True,
        help='Ingrese el NIP del operario asignado para confirmar'
    )

    def action_validate_and_start(self):
        """Validar NIP e iniciar tarea"""
        self.ensure_one()
        
        # Validar que el empleado tenga PIN configurado (campo 'pin' de Odoo)
        if not self.employee_id.pin:
            raise UserError(_(
                'El operario %s no tiene un PIN configurado. '
                'Por favor, configure el PIN en los datos del empleado (pestaña HR Settings).'
            ) % self.employee_id.name)
        
        # Validar que el PIN sea correcto
        if self.pin != self.employee_id.pin:
            raise ValidationError(_('PIN incorrecto. Verifique e intente nuevamente.'))
        
        # Si el PIN es correcto, iniciar la tarea
        self.task_id._start_task_internal()
        
        return {'type': 'ir.actions.act_window_close'}