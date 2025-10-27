from odoo import models, api, fields, _
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _inherit = 'pos.order'
    
    @api.model
    def action_reconcile_credit_note(self):
        """Abre una vista expandida mostrando cada NC como línea individual"""
        
        # Generar token único para esta búsqueda
        import uuid
        search_token = str(uuid.uuid4())
        
        # Buscar la cuenta 211040020000
        nc_account = self.env['account.account'].search([
            ('code', '=', '211040020000')
        ], limit=1)
        
        if not nc_account:
            raise UserError(_('No se encontró la cuenta 211040020000 - Notas de Crédito por Aplicar'))
        
        # Limpiar líneas anteriores
        self.env['credit.note.line.view'].search([]).unlink()
        
        # ===== BUSCAR TODAS LAS SESIONES CERRADAS =====
        today = fields.Date.today()
        first_day = today.replace(day=1)
        
        all_sessions = self.env['pos.session'].search([
            ('state', '=', 'closed'),
            ('stop_at', '>=', first_day),
        ], order='stop_at desc')
        
        for session in all_sessions:
            # Buscar NC de esta sesión
            nc_orders = self.env['pos.order'].search([
                ('session_id', '=', session.id),
                ('is_credit_note', '=', True),
            ])
            
            # Buscar órdenes normales de esta sesión que usaron NC como pago
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
                # Buscar el apunte contable de esta sesión en la cuenta NC
                move_line = False
                if session.move_id:
                    # Buscar línea con crédito (NC) o débito (Refacturación)
                    move_lines_credit = session.move_id.line_ids.filtered(
                        lambda l: l.account_id.id == nc_account.id and l.credit > 0
                    )
                    move_lines_debit = session.move_id.line_ids.filtered(
                        lambda l: l.account_id.id == nc_account.id and l.debit > 0
                    )
                    
                    # Si hay crédito, usar esa línea para NC
                    if move_lines_credit:
                        move_line = move_lines_credit[0]
                    # Si solo hay débito, es refacturación
                    elif move_lines_debit:
                        move_line = move_lines_debit[0]
                
                # Saltar si está conciliado
                if move_line and move_line.reconciled:
                    continue
                
                # Determinar el tipo basado en el pago de la sesión
                nc_type = 'nota_credito'
                if move_line:
                    if move_line.debit > 0:
                        nc_type = 'refacturacion'
                    elif move_line.credit > 0:
                        nc_type = 'nota_credito'
                
                # Determinar vendedor (usuario de la sesión)
                vendedor = session.user_id.name if session.user_id else ''
                
                # Crear UNA línea por cada NC individual
                for nc in nc_orders:
                    factura_origen = ''
                    # Buscar factura de la orden original que generó esta NC
                    if nc.origin_order_id and nc.origin_order_id.account_move:
                        factura_origen = nc.origin_order_id.account_move.name
                    
                    # Determinar debe/haber según el tipo
                    debit_amount = 0.0
                    credit_amount = 0.0
                    
                    if nc_type == 'nota_credito':
                        credit_amount = nc.credit_note_amount
                    else:
                        debit_amount = nc.credit_note_amount
                    
                    self.env['credit.note.line.view'].create({
                        'search_token': search_token,
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
            
            # Procesar refacturaciones por separado si las hay
            if has_refacturacion:
                # Buscar el apunte con débito
                move_line_debit = False
                if session.move_id:
                    move_line_debit = session.move_id.line_ids.filtered(
                        lambda l: l.account_id.id == nc_account.id and l.debit > 0
                    )
                    move_line_debit = move_line_debit[0] if move_line_debit else False
                
                # Saltar si está conciliado
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
                            self.env['credit.note.line.view'].create({
                                'search_token': search_token,
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
        created_lines = self.env['credit.note.line.view'].search_count([('search_token', '=', search_token)])
        
        # Abrir la vista
        return {
            'name': _('Libro Mayor - Notas de Crédito (%s)') % created_lines,
            'type': 'ir.actions.act_window',
            'res_model': 'credit.note.line.view',
            'view_mode': 'tree',
            'views': [(self.env.ref('sm_pos_credit_note_detail.view_credit_note_line_expanded_tree').id, 'tree')],
            'domain': [('search_token', '=', search_token)],
            'context': {'create': False, 'edit': False, 'delete': False},
            'target': 'current',
        }