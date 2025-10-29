from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ReconcileConfirmationWizard(models.TransientModel):
    _name = 'reconcile.confirmation.wizard'
    _description = 'Wizard de Confirmación de Conciliación'
    
    line_count = fields.Integer(string='Líneas Seleccionadas', readonly=True)
    total_debit = fields.Monetary(string='Total Debe', readonly=True, currency_field='currency_id')
    total_credit = fields.Monetary(string='Total Haber', readonly=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Moneda', readonly=True)
    line_details = fields.Html(string='Detalle', readonly=True)
    move_line_ids = fields.Many2many('account.move.line', string='Apuntes a Conciliar')
    
    def action_confirm_reconcile(self):
        """Ejecuta la conciliación"""
        self.ensure_one()
        
        if not self.move_line_ids:
            raise UserError(_('No hay apuntes contables para conciliar.'))
        
        if len(self.move_line_ids) < 2:
            raise UserError(_('Se requieren al menos 2 apuntes para conciliar.'))
        
        try:
            # Filtrar solo los NO conciliados
            lines_to_reconcile = self.move_line_ids.filtered(lambda l: not l.reconciled)
            
            if not lines_to_reconcile:
                raise UserError(_('Todos los apuntes ya están conciliados.'))
            
            if len(lines_to_reconcile) < 2:
                raise UserError(_('Solo hay %s apunte sin conciliar. Se necesitan al menos 2.') % len(lines_to_reconcile))
            
            lines_to_reconcile.reconcile()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('✅ Conciliación Exitosa'),
                    'message': _('Se conciliaron %s apuntes correctamente.') % len(lines_to_reconcile),
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        except Exception as e:
            raise UserError(_('❌ Error al conciliar: %s') % str(e))