def action_reconcile_lines(self):
    """Busca los asientos del diario del método de pago y los concilia"""
    
    if len(self) < 2:
        raise UserError(_('Debe seleccionar al menos 2 líneas para conciliar.'))
    
    # Buscar la cuenta 211040020000
    nc_account = self.env['account.account'].search([('code', '=', '211040020000')], limit=1)
    if not nc_account:
        raise UserError(_('No se encontró la cuenta 211040020000'))
    
    # Obtener las órdenes
    orders = self.mapped('pos_order_id').filtered(lambda o: o)
    if not orders:
        raise UserError(_('No se encontraron órdenes POS en las líneas seleccionadas'))
    
    # Buscar todos los métodos de pago "Devolución/Nota" de las órdenes
    payment_methods = self.env['pos.payment.method']
    for order in orders:
        payments = order.payment_ids.filtered(
            lambda p: 'devolución' in (p.payment_method_id.name or '').lower() or 
                     'devolucion' in (p.payment_method_id.name or '').lower() or
                     'nota' in (p.payment_method_id.name or '').lower()
        )
        payment_methods |= payments.mapped('payment_method_id')
    
    if not payment_methods:
        raise UserError(_('No se encontraron métodos de pago Devolución/Nota en las órdenes seleccionadas'))
    
    payment_methods_with_journal = payment_methods.filtered(lambda m: m.journal_id)
    if not payment_methods_with_journal:
        raise UserError(_('Los métodos de pago no tienen diario configurado'))
    
    # Obtener rango de fechas de las líneas seleccionadas (+/- 3 días)
    min_date = min(self.mapped('date')) - timedelta(days=3)
    max_date = max(self.mapped('date')) + timedelta(days=3)
    
    # Buscar TODOS los asientos en los diarios de los métodos de pago en ese rango de fechas
    move_lines_to_reconcile = self.env['account.move.line']
    
    for payment_method in payment_methods_with_journal:
        # Buscar asientos en el diario del método de pago
        moves = self.env['account.move'].search([
            ('journal_id', '=', payment_method.journal_id.id),
            ('state', '=', 'posted'),
            ('date', '>=', min_date),
            ('date', '<=', max_date),
        ])
        
        # De esos asientos, buscar líneas en cuenta 211040020000 con SALDO PENDIENTE
        for move in moves:
            nc_lines = move.line_ids.filtered(
                lambda l: l.account_id.id == nc_account.id and l.amount_residual != 0
            )
            move_lines_to_reconcile |= nc_lines
    
    if not move_lines_to_reconcile:
        # Mensaje de debug más detallado
        error_msg = 'No se encontraron asientos contables con saldo pendiente.\n\n'
        error_msg += 'Informacion de busqueda:\n'
        error_msg += '- Metodos de pago: %s\n' % ', '.join(payment_methods_with_journal.mapped('name'))
        error_msg += '- Diarios: %s\n' % ', '.join(payment_methods_with_journal.mapped('journal_id.name'))
        error_msg += '- Cuenta: %s\n' % nc_account.code
        error_msg += '- Rango de fechas: %s a %s\n' % (min_date, max_date)
        error_msg += '- Ordenes: %s\n' % len(orders)
        
        # Verificar si hay asientos en el diario
        all_moves = self.env['account.move'].search([
            ('journal_id', 'in', payment_methods_with_journal.mapped('journal_id').ids),
            ('state', '=', 'posted'),
            ('date', '>=', min_date),
            ('date', '<=', max_date),
        ])
        
        if all_moves:
            error_msg += '\nSe encontraron %s asientos en los diarios.\n' % len(all_moves)
            
            # Verificar líneas en la cuenta
            all_lines = all_moves.mapped('line_ids').filtered(lambda l: l.account_id.id == nc_account.id)
            if all_lines:
                with_residual = all_lines.filtered(lambda l: l.amount_residual != 0)
                fully_reconciled = all_lines.filtered(lambda l: l.amount_residual == 0)
                error_msg += 'Se encontraron %s lineas en la cuenta %s:\n' % (len(all_lines), nc_account.code)
                error_msg += '- %s lineas con saldo pendiente\n' % len(with_residual)
                error_msg += '- %s lineas totalmente conciliadas (saldo = 0)\n' % len(fully_reconciled)
        else:
            error_msg += '\nNo se encontraron asientos en los diarios especificados para ese rango de fechas.'
        
        raise UserError(_(error_msg))
    
    if len(move_lines_to_reconcile) < 2:
        raise UserError(_('Solo se encontró 1 asiento con saldo pendiente. Se necesitan al menos 2 para conciliar.'))
    
    # Calcular totales
    total_debit = sum(self.mapped('debit'))
    total_credit = sum(self.mapped('credit'))
    
    # Construir HTML
    html = '<h4>Lineas Seleccionadas:</h4>'
    html += '<table style="width:100%; border-collapse: collapse; margin-bottom: 20px;">'
    html += '<tr style="background-color: #f0f0f0; font-weight: bold;">'
    html += '<th style="padding: 8px; border: 1px solid #ddd;">Fecha</th>'
    html += '<th style="padding: 8px; border: 1px solid #ddd;">Sesion</th>'
    html += '<th style="padding: 8px; border: 1px solid #ddd;">Orden</th>'
    html += '<th style="padding: 8px; border: 1px solid #ddd;">Tipo</th>'
    html += '<th style="padding: 8px; border: 1px solid #ddd;">Debe</th>'
    html += '<th style="padding: 8px; border: 1px solid #ddd;">Haber</th>'
    html += '</tr>'
    
    for line in self:
        tipo = 'NC' if line.nc_type == 'nota_credito' else 'Refacturacion'
        html += '<tr>'
        html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % line.date
        html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % (line.session_name or '')
        html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % line.name
        html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % tipo
        html += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">Q %.2f</td>' % line.debit
        html += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">Q %.2f</td>' % line.credit
        html += '</tr>'
    
    html += '<tr style="background-color: #e8f5e9; font-weight: bold;">'
    html += '<td colspan="4" style="padding: 8px; border: 1px solid #ddd; text-align: right;">TOTAL:</td>'
    html += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">Q %.2f</td>' % total_debit
    html += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">Q %.2f</td>' % total_credit
    html += '</tr>'
    html += '</table>'
    
    # Asientos encontrados
    html += '<hr/><h4>Asientos Contables a Conciliar (con saldo pendiente):</h4>'
    html += '<p><strong>Metodos de Pago:</strong> %s</p>' % ', '.join(payment_methods_with_journal.mapped('name'))
    html += '<p><strong>Diarios:</strong> %s</p>' % ', '.join(payment_methods_with_journal.mapped('journal_id.name'))
    html += '<p><strong>Total de asientos:</strong> %s</p>' % len(move_lines_to_reconcile)
    html += '<table style="width:100%; border-collapse: collapse;">'
    html += '<tr style="background-color: #e3f2fd; font-weight: bold;">'
    html += '<th style="padding: 8px; border: 1px solid #ddd;">Asiento</th>'
    html += '<th style="padding: 8px; border: 1px solid #ddd;">Diario</th>'
    html += '<th style="padding: 8px; border: 1px solid #ddd;">Ref</th>'
    html += '<th style="padding: 8px; border: 1px solid #ddd;">Fecha</th>'
    html += '<th style="padding: 8px; border: 1px solid #ddd;">Cuenta</th>'
    html += '<th style="padding: 8px; border: 1px solid #ddd;">Debe</th>'
    html += '<th style="padding: 8px; border: 1px solid #ddd;">Haber</th>'
    html += '<th style="padding: 8px; border: 1px solid #ddd;">Saldo</th>'
    html += '</tr>'
    
    move_debit = 0
    move_credit = 0
    for ml in move_lines_to_reconcile:
        html += '<tr>'
        html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % ml.move_id.name
        html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % ml.move_id.journal_id.name
        html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % (ml.move_id.ref or '-')
        html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % ml.date
        html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % ml.account_id.code
        html += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">Q %.2f</td>' % ml.debit
        html += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">Q %.2f</td>' % ml.credit
        html += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right; font-weight: bold;">Q %.2f</td>' % abs(ml.amount_residual)
        html += '</tr>'
        move_debit += ml.debit
        move_credit += ml.credit
    
    html += '<tr style="background-color: #4caf50; color: white; font-weight: bold;">'
    html += '<td colspan="5" style="padding: 10px; border: 2px solid #4caf50; text-align: right;">TOTAL ASIENTOS:</td>'
    html += '<td style="padding: 10px; border: 2px solid #4caf50; text-align: right;">Q %.2f</td>' % move_debit
    html += '<td style="padding: 10px; border: 2px solid #4caf50; text-align: right;">Q %.2f</td>' % move_credit
    html += '<td style="padding: 10px; border: 2px solid #4caf50; text-align: right;"></td>'
    html += '</tr>'
    html += '</table>'
    
    # Crear wizard
    wizard = self.env['reconcile.confirmation.wizard'].create({
        'line_count': len(self),
        'total_debit': total_debit,
        'total_credit': total_credit,
        'currency_id': self[0].currency_id.id,
        'line_details': html,
        'move_line_ids': [(6, 0, move_lines_to_reconcile.ids)],
    })
    
    return {
        'name': _('Confirmar Conciliacion'),
        'type': 'ir.actions.act_window',
        'res_model': 'reconcile.confirmation.wizard',
        'view_mode': 'form',
        'res_id': wizard.id,
        'target': 'new',
    }