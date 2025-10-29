from odoo import models, api, fields, _
from odoo.exceptions import UserError
from datetime import timedelta


class PosOrder(models.Model):
    _inherit = 'pos.order'
    
    @api.model
    def load_credit_notes_view(self):
        """Carga la vista de notas de crédito"""
        
        # Buscar la cuenta 211040020000
        nc_account = self.env['account.account'].search([('code', '=', '211040020000')], limit=1)
        if not nc_account:
            raise UserError(_('No se encontró la cuenta 211040020000'))
        
        # Limpiar datos anteriores
        self.env['credit.note.line'].search([]).unlink()
        
        # Fecha inicio - ÚLTIMOS 6 MESES para asegurar que hay datos
        today = fields.Date.today()
        six_months_ago = today - timedelta(days=180)
        
        # Buscar sesiones cerradas de los últimos 6 meses
        sessions = self.env['pos.session'].search([
            ('state', '=', 'closed'),
            ('stop_at', '>=', six_months_ago),
        ], order='stop_at desc')
        
        if not sessions:
            raise UserError(_('No se encontraron sesiones cerradas en los últimos 6 meses'))
        
        # Procesar cada sesión
        lines_created = 0
        for session in sessions:
            lines_created += self._process_session(session, nc_account)
        
        if lines_created == 0:
            raise UserError(_('Se encontraron %s sesiones pero no se crearon líneas. Todas las NC están conciliadas o no hay NC.') % len(sessions))
        
        # Abrir la vista
        return {
            'name': _('Libro Mayor - Notas de Crédito (%s líneas)') % lines_created,
            'type': 'ir.actions.act_window',
            'res_model': 'credit.note.line',
            'view_mode': 'tree',
            'target': 'current',
            'context': {'create': False, 'edit': False, 'delete': False},
        }
    
    
def _process_session(self, session, nc_account):
    """Procesa una sesión y crea las líneas de NC"""
    lines_created = 0
    
    # Buscar NC de la sesión
    nc_orders = self.env['pos.order'].search([
        ('session_id', '=', session.id),
        ('is_credit_note', '=', True),
    ])
    
    if not nc_orders:
        return 0
    
    # Buscar el asiento contable del método de pago
    nc_payment_move_line = False
    
    # Buscar pagos con método "Devolución" o "Nota" de esta sesión
    nc_payments = self.env['pos.payment'].search([
        ('session_id', '=', session.id),
    ]).filtered(
        lambda p: 'devolución' in (p.payment_method_id.name or '').lower() or 
                 'devolucion' in (p.payment_method_id.name or '').lower() or
                 'nota' in (p.payment_method_id.name or '').lower()
    )
    
    if nc_payments:
        payment_method = nc_payments[0].payment_method_id
        if payment_method.journal_id:
            # Buscar asientos en el diario del método de pago de esta sesión
            moves = self.env['account.move'].search([
                ('journal_id', '=', payment_method.journal_id.id),
                ('state', '=', 'posted'),
                ('date', '=', session.stop_at.date() if session.stop_at else fields.Date.today()),
            ])
            
            for move in moves:
                nc_lines = move.line_ids.filtered(
                    lambda l: l.account_id.id == nc_account.id
                )
                if nc_lines:
                    nc_payment_move_line = nc_lines[0]
                    break
    
    # NO FILTRAR POR CONCILIADO - puede tener saldo pendiente
    # Ya no validamos: if nc_payment_move_line and nc_payment_move_line.reconciled: return 0
    
    # Determinar tipo
    nc_type = 'nota_credito'
    if nc_payment_move_line and nc_payment_move_line.debit > 0:
        nc_type = 'refacturacion'
    
    # Crear línea por cada NC
    for nc in nc_orders:
        factura_origen = ''
        if nc.origin_order_id and nc.origin_order_id.account_move:
            factura_origen = nc.origin_order_id.account_move.name
        
        self.env['credit.note.line'].create({
            'date': nc.date_order.date() if nc.date_order else fields.Date.today(),
            'name': nc.pos_reference or nc.name,
            'account_id': nc_account.id,
            'session_name': session.name,
            'nc_type': nc_type,
            'description': 'NC del %s factura nota %s' % (session.name, factura_origen),
            'debit': nc.credit_note_amount if nc_type == 'refacturacion' else 0.0,
            'credit': nc.credit_note_amount if nc_type == 'nota_credito' else 0.0,
            'currency_id': nc.currency_id.id,
            'vendedor': session.user_id.name if session.user_id else '',
            'move_line_id': nc_payment_move_line.id if nc_payment_move_line else False,
            'pos_order_id': nc.id,
        })
        lines_created += 1
    
    # Procesar refacturaciones (órdenes que pagaron con NC)
    orders = self.env['pos.order'].search([
        ('session_id', '=', session.id),
        ('amount_total', '>', 0),
    ])
    
    for order in orders:
        nc_payments = order.payment_ids.filtered(
            lambda p: 'devolución' in (p.payment_method_id.name or '').lower() or 
                     'devolucion' in (p.payment_method_id.name or '').lower() or
                     'nota' in (p.payment_method_id.name or '').lower()
        )
        
        if nc_payments:
            # Buscar el asiento de refacturación
            refund_move_line = False
            
            if nc_payments and nc_payments[0].payment_method_id.journal_id:
                payment_method = nc_payments[0].payment_method_id
                moves = self.env['account.move'].search([
                    ('journal_id', '=', payment_method.journal_id.id),
                    ('state', '=', 'posted'),
                    ('date', '=', session.stop_at.date() if session.stop_at else fields.Date.today()),
                ])
                
                for move in moves:
                    refund_lines = move.line_ids.filtered(
                        lambda l: l.account_id.id == nc_account.id and l.debit > 0
                    )
                    if refund_lines:
                        refund_move_line = refund_lines[0]
                        break
            
            # NO FILTRAR POR CONCILIADO - puede tener saldo pendiente
            
            for payment in nc_payments:
                self.env['credit.note.line'].create({
                    'date': order.date_order.date() if order.date_order else fields.Date.today(),
                    'name': order.pos_reference or order.name,
                    'account_id': nc_account.id,
                    'session_name': session.name,
                    'nc_type': 'refacturacion',
                    'description': 'Orden %s Uso NC' % (order.pos_reference or order.name),
                    'debit': abs(payment.amount),
                    'credit': 0.0,
                    'currency_id': order.currency_id.id,
                    'vendedor': session.user_id.name if session.user_id else '',
                    'move_line_id': refund_move_line.id if refund_move_line else False,
                    'pos_order_id': order.id,
                })
                lines_created += 1
    
    return lines_created