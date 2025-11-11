# Copyright (C) 2015-Today GRAP (http://www.grap.coop)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare
from dateutil.tz import gettz

class PosPaymentChangeWizard(models.TransientModel):
    _name = "pos.payment.change.wizard"
    _description = "PoS Payment Change Wizard"
    
    POS_SESSION_STATE = [
        ('opening_control', 'Opening Control'),  # method action_pos_session_open
        ('opened', 'In Progress'),               # method action_pos_session_closing_control
        ('closing_control', 'Closing Control'),  # method action_pos_session_close
        ('closed', 'Closed & Posted'),
    ]

    # Column Section
    order_id = fields.Many2one(comodel_name="pos.order", string="Order", readonly=True)
    session_id = fields.Many2one(comodel_name="pos.session", related="order_id.session_id")
    session_state = fields.Selection(string='Status', related='session_id.state')
    close_session_reason = fields.Char(string="Razón de cambio de pago", help="Indica la razón por la cual se desea realizar el cambio de método de pago con la sesión ya cerrada")
    
    old_line_ids = fields.One2many(
        comodel_name="pos.payment.change.wizard.old.line",
        inverse_name="wizard_id",
        string="Old Payment Lines",
        readonly=True,
    )

    new_line_ids = fields.One2many(
        comodel_name="pos.payment.change.wizard.new.line",
        inverse_name="wizard_id",
        string="New Payment Lines",
    )

    amount_total = fields.Float(string="Total", readonly=True)

    # View Section
    @api.model
    def default_get(self, fields):
        PosOrder = self.env["pos.order"]
        res = super().default_get(fields)
        order = PosOrder.browse(self._context.get("active_id"))
        old_lines_vals = []
        for payment in order.payment_ids:
            old_lines_vals.append(
                (
                    0,
                    0,
                    {
                        "old_payment_method_id": payment.payment_method_id.id,
                        "amount": payment.amount,
                    },
                )
            )
        res.update(
            {
                "order_id": order.id,
                "amount_total": order.amount_total,
                "old_line_ids": old_lines_vals,
            }
        )
        return res

    # View section
    def button_change_payment(self):
        self.ensure_one()
        order = self.order_id

        # Check if the total is correct
        total = sum(self.mapped("new_line_ids.amount"))
        if (
            float_compare(
                total,
                self.amount_total,
                precision_rounding=self.order_id.currency_id.rounding,
            )
            != 0
        ):
            raise UserError(
                _(
                    "Differences between the two values for the POS"
                    " Order '%(name)s':\n\n"
                    " * Total of all the new payments %(total)s;\n"
                    " * Total of the POS Order %(amount_total)s;\n\n"
                    "Please change the payments.",
                    name=order.name,
                    total=total,
                    amount_total=order.amount_total,
                )
            )

        # Change payment
        new_payments = [
            {
                "pos_order_id": order.id,
                "payment_method_id": line.new_payment_method_id.id,
                "amount": line.amount,
                "payment_date": fields.Date.context_today(self),
            }
            for line in self.new_line_ids
        ]

        if self.close_session_reason:
            order.write({"close_session_reason": self.close_session_reason})
            order.session_id.write({'state':'closing_control'})

            if order.session_id.move_id:
                
                session_matching_numbers = []
                for move_line in order.session_id.move_id.line_ids:
                    if move_line.matching_number:
                        session_matching_numbers.append(move_line.matching_number)
                
                #Get the bank statement lines for Cash operations
                account_move_cash_data = self.env['account.move.line'].search([
                    ('matching_number', 'in', session_matching_numbers),
                    ('statement_line_id', '!=', False)
                ])
                for move_line in account_move_cash_data:
                    if move_line.statement_line_id:
                        statement_line_id = move_line.statement_line_id
                        move_line.statement_line_id.action_undo_reconciliation()
                        statement_line_id.write({"pos_session_id": False})
                        statement_line_id.unlink()
                
                #Get the non Cash operations
                account_move_nocash_data = self.env['account.move.line'].search([
                    ('matching_number', 'in', session_matching_numbers),
                    ('payment_id', '!=', False)
                ])
                for move_line in account_move_nocash_data:
                    payment_id = move_line.payment_id
                    payment_id.action_draft()
                    payment_id.action_cancel()
                    
    
    
        orders = order.change_payment(new_payments)
        
        if self.close_session_reason:            
            order.session_id.move_id.button_draft()
            order.session_id.move_id.button_cancel()
            order.session_id.action_pos_session_closing_control()
            self.env.cr.commit()
            msg_body = ("Se modifico el pago del pedido %s y reproceso el cierre. Motivo: %s") % (order.name, self.close_session_reason)
            order.session_id.message_post(body=msg_body)
            order.message_post(body=msg_body)
            #order.session_id.move_id.unlink()
            session_date = order.session_id.stop_at.astimezone(gettz("America/Guatemala")).strftime("%Y-%m-%d")

            matching_numbers = []
            payment_ids = []
            payment_move_ids = []
            for move_line in order.session_id.move_id.line_ids:
                if move_line.matching_number:
                    matching_numbers.append(move_line.matching_number)
                    
            if len(matching_numbers) > 0:
                sql = "SELECT id, payment_id, move_id FROM account_move_line"
                sql += " WHERE matching_number IN %(matching_numbers)s"
                sql += " AND payment_id IS NOT NULL"
                params = {
                    "matching_numbers": tuple(matching_numbers),
                }
                self.env.cr.execute(sql, params)
                result = self.env.cr.fetchall()
                for row in result:
                    payment_ids.append(row[1])
                    payment_move_ids.append(row[2])


            #Updating payments
            if len(payment_ids) > 0:
                #Update date for payments
                """sql = "UPDATE account_payment"
                sql += " SET date = %(session_date)s"
                sql += " WHERE id IN %(payment_ids)s"
                params = {
                    "session_date": session_date,
                    "payment_ids": tuple(payment_ids),
                }
                self.env.cr.execute(sql, params)"""

                sql = "UPDATE account_move_line"
                sql += " SET date = %(session_date)s, date_maturity = %(session_date)s"
                sql += " WHERE move_id IN %(payment_move_ids)s"
                params = {
                    "session_date": session_date,
                    "payment_move_ids": tuple(payment_move_ids),
                }
                self.env.cr.execute(sql, params)


                sql = "UPDATE account_move"
                sql += " SET date = %(session_date)s"
                sql += " WHERE id IN %(payment_move_ids)s"
                params = {
                    "session_date": session_date,
                    "payment_move_ids": tuple(payment_move_ids),
                }
                self.env.cr.execute(sql, params)

            #Updating matching operations
            if len(matching_numbers) > 0:
                sql = "UPDATE account_move_line"
                sql += " SET date = %(session_date)s, date_maturity = %(session_date)s"
                sql += " WHERE matching_number IN %(matching_numbers)s"
                
                params = {
                    "session_date": session_date,
                    "matching_numbers": tuple(matching_numbers),
                }
                self.env.cr.execute(sql, params)

            #Bank statement lines
            sql = "SELECT move_id"
            sql += " FROM account_bank_statement_line"
            sql += " WHERE pos_session_id = %(session_id)s"
            params = {
                "session_id": order.session_id.id,
            }
            self.env.cr.execute(sql, params)
            result = self.env.cr.fetchall()
            bank_move_ids = [row[0] for row in result]


            if len(bank_move_ids) > 0:
                sql = "UPDATE account_move_line"
                sql += " SET date = %(session_date)s, date_maturity = %(session_date)s"
                sql += " WHERE move_id IN %(move_ids)s"

                params = {
                    "session_date": session_date,
                    "move_ids": tuple(bank_move_ids),
                }
                self.env.cr.execute(sql, params)

                sql = "UPDATE account_move"
                sql += " SET date = %(session_date)s"
                sql += " WHERE id IN %(move_ids)s"
                params = {
                    "session_date": session_date,
                    "move_ids": tuple(bank_move_ids),
                }
                self.env.cr.execute(sql, params)
                
            sql = "UPDATE account_move_line"
            sql += " SET date = %(session_date)s, date_maturity = %(session_date)s"
            sql += " WHERE move_id = %(move_id)s"

            params = {
                "session_date": session_date,
                "move_id": order.session_id.move_id.id,
            }
            self.env.cr.execute(sql, params)

            sql = "UPDATE account_move"
            sql += " SET date = %(session_date)s"
            sql += " WHERE id = %(move_id)s"

            params = {
                "session_date": session_date,
                "move_id": order.session_id.move_id.id,
            }
            self.env.cr.execute(sql, params)


            

        if len(orders) == 1:
            # if policy is 'update', only close the pop up
            action = {"type": "ir.actions.act_window_close"}
        else:
            # otherwise (refund policy), displays the 3 orders
            action = self.env.ref("point_of_sale.action_pos_pos_form").read()[0]
            action["domain"] = [("id", "in", orders.ids)]

        return action
