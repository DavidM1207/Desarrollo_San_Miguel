from odoo import models, api, fields, _
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _inherit = 'pos.order'
    
    @api.model
    def load_credit_notes_view(self):
        """Carga la vista de notas de crédito"""
        
        # Generar token único
        import uuid
        search_token = str(uuid.uuid4())
        
        # Buscar la cuenta 211040020000
        nc_account = self.env['account.account'].search([('code', '=', '211040020000')], limit=1)
        if not nc_account:
            raise UserError(_('No se encontró la cuenta 211040020000'))
        
        # Limpiar datos anteriores
        self.env['credit.note.line.view'].search([]).unlink()
        
        # Fecha inicio del mes actual
        today = fields.Date.today()
        first_day = today.replace(day=1)
        
        # Buscar sesiones cerradas del mes actual
        sessions = self.env['pos.session'].search([
            ('state', '=', 'closed'),
            ('stop_at', '>=', first_day),
        ], order='stop_at desc')
        
        # Procesar cada sesión
        lines_created = 0
        for session in sessions:
            lines_created += self._process_session(session, nc_account, search_token)
        
        # Abrir la vista
        return {
            'name': _('Libro Mayor - Notas de Crédito (%s líneas)') % lines_created,
            'type': 'ir.actions.act_window',
            'res_model': 'credit.note.line.view',
            'view_mode': 'tree',
            'views': [(self.env.ref('sm_pos_credit_note_detail.view_credit_note_line_expanded_tree').id, 'tree')],
            'domain': [('search_token', '=', search_token)],
            'target': 'current',
            'context': {'create': False, 'edit': False, 'delete': False},
        }
    
    def _process_session(self, session, nc_account, search_token):
        """Procesa una sesión y crea las líneas de NC"""
        lines_created = 0
        
        # Buscar NC de la sesión usando is_credit_note
        nc_orders = self.env['pos.order'].search([
            ('session_id', '=', session.id),
            ('is_credit_note', '=', True),
        ])
        
        if not nc_orders:
            return 0
        
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
        
        # Si está conciliado, saltar
        if move_line and move_line.reconciled:
            return 0
        
        # Determinar tipo
        nc_type = 'nota_credito'
        if move_line and move_line.debit > 0:
            nc_type = 'refacturacion'
        
        vendedor = session.user_id.name if session.user_id else ''
        
        # Crear línea por cada NC
        for nc in nc_orders:
            factura_origen = ''
            if nc.origin_order_id and nc.origin_order_id.account_move:
                factura_origen = nc.origin_order_id.account_move.name
            
            self.env['credit.note.line.view'].create({
                'search_token': search_token,
                'date': nc.date_order.date() if nc.date_order else fields.Date.today(),
                'name': nc.pos_reference or nc.name,
                'account_id': nc_account.id,
                'session_name': session.name,
                'nc_type': nc_type,
                'description': 'NC del %s factura nota %s' % (session.name, factura_origen),
                'debit': nc.credit_note_amount if nc_type == 'refacturacion' else 0.0,
                'credit': nc.credit_note_amount if nc_type == 'nota_credito' else 0.0,
                'currency_id': nc.currency_id.id,
                'vendedor': vendedor,
                'move_line_id': move_line.id if move_line else False,
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
                lambda p: 'crédit' in (p.payment_method_id.name or '').lower() or 
                         'credit' in (p.payment_method_id.name or '').lower() or
                         'nota' in (p.payment_method_id.name or '').lower()
            )
            
            if nc_payments:
                move_line_debit = False
                if session.move_id:
                    move_line_debit = session.move_id.line_ids.filtered(
                        lambda l: l.account_id.id == nc_account.id and l.debit > 0
                    )
                    move_line_debit = move_line_debit[0] if move_line_debit else False
                
                if move_line_debit and move_line_debit.reconciled:
                    continue
                
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
                    lines_created += 1
        
        return lines_created