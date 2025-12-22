# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class TrackerTaskPinWizard(models.TransientModel):
    _name = 'tracker.task.pin.wizard'
    _description = 'Wizard para validar NIP en acciones de tarea'

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
    
    action_type = fields.Char(
        string='Tipo de Acción',
        help='start, pause, o complete'
    )

    def action_validate_and_execute(self):
        """Validar NIP y ejecutar la acción correspondiente"""
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
        
        # Obtener el tipo de acción del contexto
        action_type = self.env.context.get('action_type', 'start')
        
        # Ejecutar la acción correspondiente
        if action_type == 'start':
            self.task_id._start_task_internal()
        elif action_type == 'pause':
            self.task_id._execute_pause()
        elif action_type == 'complete':
            self.task_id._execute_complete()
        
        return {'type': 'ir.actions.act_window_close'}
    
    # Mantener compatibilidad con método anterior
    def action_validate_and_start(self):
        """Método legacy para compatibilidad"""
        return self.action_validate_and_execute()