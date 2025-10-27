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
        
        # Fecha inicio del mes actual
        today = fields.Date.today()
        first_day = today.replace(day=1)
        
        # Buscar todas las sesiones cerradas del mes actual
        all_sessions = self.env['pos.session'].search([
            ('state', '=', 'closed'),
            ('stop_at', '>=', first_day),
        ], order='stop_at desc')
        
        # Procesar cada sesión
        for session in all_sessions:
            # Buscar NC de esta sesión
            nc_orders = self.env['pos.order'].search([
                ('session_id', '=', session.id),
                ('is_credit_note', '=', True),
            ])
            
            # Buscar órdenes normales que usaron NC como pago
            orders_with_nc = self.env['pos.order'].search([
                ('session_id', '=', session.id),
                ('amount_total', '>', 0),
            ])
            
            has_refacturacion = False
            for order in orders_with_nc:
                nc_payments = order.payment_ids.filtered(
                    lambda p: 'crédit' in (p.payment_method_id.name or '').lower() or 
                             'credit' in (p.payment_method_id.name or '').lower() or
                             'nota' in (p.payment_method_id.name or '').lower()
                )
                if nc_payments:
                    has_refacturacion = True
                    break
            
            if nc_orders:
                # Buscar el apunte contable
                move_line = False
                if session.move_id:
                    move_lines_credit = session.move_id.line_ids.filtered(
                        lambda l: l.account_id.id == nc_account.id and l.credit > 0
                    )
                    move_lines_debit = session.move_id.line_ids.filtered(
                        lambda l: l.account_id.id == nc_account.id and l.debit > 0
                    )
                    
                    if move_lines_credit:
                        move_line = move_lines_credit[0]
                    elif move_lines_debit:
                        move_line = move_lines_debit[0]
                
                # Saltar si está conciliado
                if move_line and move_line.reconciled:
                    continue
                
                # Determinar tipo basado en el apunte contable
                nc_type = 'nota_credito'
                if move_line:
                    if move_line.debit > 0:
                        nc_type = 'refacturacion'
                    elif move_line.credit > 0:
                        nc_type = 'nota_credito'
                
                vendedor = session.user_id.name if session.user_id else ''
                
                # Crear UNA línea por cada NC individual
                for nc in nc_orders:
                    factura_origen = ''
                    if nc.origin_order_id and nc.origin_order_id.account_move:
                        factura_origen = nc.origin_order_id.account_move.name
                    
                    debit_amount = 0.0
                    credit_amount = 0.0
                    
                    if nc_type == 'nota_credito':
                        credit_amount = nc.credit_note_amount
                    else:
                        debit_amount = nc.credit_note_amount
                    
                    self.env['credit.note.line'].create({
                        'date': nc.date_order.date() if nc.date_order else fields.Date.today(),
                        'name': nc.pos_reference or nc.name,
                        'account_id': nc_account.id,
                        'session_name': session.name,
                        'nc_type': nc_type,
                        'description': 'NC del %s factura nota %s' % (session.name, factura_origen),
                        'debit': debit_amount,
                        'credit': credit_amount,
                        'currency_id': nc.currency_id.id,
                        'vendedor': vendedor,
                        'move_line_id': move_line.id if move_line else False,
                        'pos_order_id': nc.id,
                    })
            
            # Procesar refacturaciones por separado
            if has_refacturacion:
                move_line_debit = False
                if session.move_id:
                    move_line_debit = session.move_id.line_ids.filtered(
                        lambda l: l.account_id.id == nc_account.id and l.debit > 0
                    )
                    move_line_debit = move_line_debit[0] if move_line_debit else False
                
                if move_line_debit and move_line_debit.reconciled:
                    continue
                
                vendedor = session.user_id.name if session.user_id else ''
                
                for order in orders_with_nc:
                    nc_payments = order.payment_ids.filtered(
                        lambda p: 'crédit' in (p.payment_method_id.name or '').lower() or 
                                 'credit' in (p.payment_method_id.name or '').lower() or
                                 'nota' in (p.payment_method_id.name or '').lower()
                    )
                    
                    if nc_payments:
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
                                'vendedor': vendedor,
                                'move_line_id': move_line_debit.id if move_line_debit else False,
                                'pos_order_id': order.id,
                            })
        
        # Contar líneas creadas
        created_lines = self.env['credit.note.line'].search_count([])
        
        # Abrir la vista siempre
        return {
            'name': _('Libro Mayor - Notas de Crédito') + (' (%s)' % created_lines if created_lines > 0 else ' (Sin registros)'),
            'type': 'ir.actions.act_window',
            'res_model': 'credit.note.line',
            'view_mode': 'tree',
            'target': 'current',
            'context': {'create': False, 'edit': False, 'delete': False},
        }