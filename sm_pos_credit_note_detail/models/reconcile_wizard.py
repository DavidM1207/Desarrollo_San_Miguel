from odoo import models, fields, _
from odoo.exceptions import UserError


class ReconcileConfirmationWizard(models.TransientModel):
    _name = 'reconcile.confirmation.wizard'
    _description = 'Wizard de Confirmación de Conciliación'
    
    line_count = fields.Integer(string='Líneas Seleccionadas', readonly=True)
    lines_with_move = fields.Integer(string='Líneas con Apunte Contable', readonly=True)
    total_debit = fields.Monetary(string='Total Debe', readonly=True, currency_field='currency_id')
    total_credit = fields.Monetary(string='Total Haber', readonly=True, currency_field='currency_id')
    difference = fields.Monetary(string='Diferencia', readonly=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Moneda', readonly=True)
    line_details = fields.Html(string='Detalle', readonly=True)
    move_line_ids = fields.Many2many('account.move.line', string='Apuntes a Conciliar')
    
    def action_confirm_reconcile(self):
        """Ejecuta la conciliación"""
        self.ensure_one()
        
        if not self.move_line_ids:
            raise UserError(_('No hay apuntes contables asociados para conciliar. Las líneas seleccionadas no tienen apuntes contables válidos.'))
        
        if len(self.move_line_ids) < 2:
            raise UserError(_('Se requieren al menos 2 apuntes contables para conciliar. Solo %s línea tiene apunte contable.') % len(self.move_line_ids))
        
        try:
            self.move_line_ids.reconcile()
            
            # Recargar los datos después de conciliar
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Conciliación Exitosa'),
                    'message': _('Se conciliaron %s apuntes correctamente.') % len(self.move_line_ids),
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        except Exception as e:
            raise UserError(_('Error al conciliar: %s') % str(e))