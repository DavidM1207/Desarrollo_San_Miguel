# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class TrackerProjectCancelWizard(models.TransientModel):
    _name = 'tracker.project.cancel.wizard'
    _description = 'Wizard para Anular Proyecto'
    
    project_id = fields.Many2one(
        'tracker.project',
        string='Proyecto',
        required=True,
        readonly=True
    )
    
    cancellation_reason = fields.Text(
        string='Motivo de Anulación',
        required=True,
        help='Especifique el motivo por el cual se anula el proyecto'
    )
    
    def action_confirm_cancel(self):
        """Anular el proyecto con el motivo especificado"""
        self.ensure_one()
        
        if not self.cancellation_reason:
            raise UserError(_('Debe especificar un motivo de anulación.'))
        
        # Actualizar notas del proyecto
        notes = self.project_id.notes or ''
        cancellation_note = f"\n\n=== PROYECTO ANULADO ===\n"
        cancellation_note += f"Fecha: {fields.Datetime.now()}\n"
        cancellation_note += f"Usuario: {self.env.user.name}\n"
        cancellation_note += f"Motivo: {self.cancellation_reason}\n"
        cancellation_note += "======================="
        
        # Anular proyecto
        self.project_id.write({
            'state': 'cancel',
            'cancellation_reason': self.cancellation_reason,
            'notes': notes + cancellation_note
        })
        
        # Anular todas las tareas del proyecto
        self.project_id.task_ids.write({'state': 'cancel'})
        
        return {'type': 'ir.actions.act_window_close'}