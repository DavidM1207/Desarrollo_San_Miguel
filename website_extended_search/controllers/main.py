from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.osv.expression import OR


class WebsiteSaleExtended(WebsiteSale):

    def _get_search_domain(self, search, category=None, attrib_values=None):
        domain = super()._get_search_domain(search, category, attrib_values)

        if search:
            search_root = search[:-1] if len(search) > 2 else search
            extended_domain = OR([
                [('name', 'ilike', search_root)],
                [('default_code', 'ilike', search)],
                [('website_description', 'ilike', search)],
                [('description_sale', 'ilike', search)],
                [('categ_id.name', 'ilike', search_root)],
                [('tag_ids.name', 'ilike', search_root)],
                [('attribute_line_ids.value_ids.name', 'ilike', search_root)],
            ])

            domain = OR([domain, extended_domain])

        return domain
