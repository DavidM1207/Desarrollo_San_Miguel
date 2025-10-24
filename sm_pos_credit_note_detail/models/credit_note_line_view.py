from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CreditNoteLineView(models.TransientModel):
    _name = 'credit.note.line.view'
    _description = 'Vista Expandida de Líneas de NC'
    _order = 'date, id'
    
    # Campo para agrupar todas las líneas de una misma búsqueda
    search_token = fields.Char(string='Token de Búsqueda', index=True)
    
    # Campos visibles en la tabla
    date = fields.Date(string='Fecha', required=True)
    name = fields.Char(string='Orden', required=True)  # Cambiado de "Asiento" a "Orden"
    account_id = fields.Many2one('account.account', string='Cuenta', required=True)
    session_name = fields.Char(string='Sesión POS')
    nc_type = fields.Selection([
        ('nota_credito', 'Nota de Crédito'),
        ('refacturacion', 'Refacturación'),
    ], string='Tipo', required=True)
    description = fields.Text(string='Detalle NC')
    debit = fields.Monetary(string='Debe', currency_field='currency_id')
    credit = fields.Monetary(string='Haber', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Moneda')
    vendedor = fields.Char(string='Vendedor')  # Cambiado de "analytic_distribution"
    
    # Campos ocultos de control
    move_line_id = fields.Many2one('account.move.line', string='Apunte Contable Real')
    pos_order_id = fields.Many2one('pos.order', string='Orden POS')
    reconciled = fields.Boolean(string='Conciliado', related='move_line_id.reconciled', store=False)
    
    def action_reconcile_lines(self):
        """Acción que se ejecuta desde el menú Acción para reconciliar líneas seleccionadas"""
        # Obtener las líneas reales de account.move.line
        move_lines = self.mapped('move_line_id').filtered(lambda l: l and not l.reconciled)
        
        if not move_lines:
            raise UserError(_('No hay líneas válidas para conciliar. Asegúrese de seleccionar líneas no conciliadas.'))
        
        if len(move_lines) < 2:
            raise UserError(_('Debe seleccionar al menos 2 líneas para conciliar.'))
        
        # Intentar conciliar usando el método nativo de Odoo
        try:
            move_lines.reconcile()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Éxito'),
                    'message': _('Se conciliaron %s apuntes correctamente.') % len(move_lines),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_('Error al conciliar: %s') % str(e))