from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    skip_payment_step = fields.Boolean(related='website_id.skip_payment_step', readonly=False)
    skip_payment_message = fields.Text(related='website_id.skip_payment_message', readonly=False)
    helpdesk_team_id = fields.Many2one(related='website_id.helpdesk_team_id', readonly=False)
    helpdesk_notify_customer = fields.Boolean(related='website_id.helpdesk_notify_customer', readonly=False)
    website_warehouses_ids = fields.Many2many('stock.warehouse', related='website_id.website_warehouses_ids', domain="[('company_id', '=', website_company_id)]", readonly=False)
