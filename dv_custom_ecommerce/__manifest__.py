{
    'name': 'DV Custom Ecommerce',
    'version': '1.0.1',
    'category': 'Website/Website',
    'summary': 'Custom ecommerce functionality',
    'author': "William Valencia",
    'maintainer': 'GTWONBAT',
    'website': 'https://gtwonbat.com',
    'depends': ['website', 'website_sale', 'website_sale_stock', 'sale', 'contacts', 'pt_nit_verification', 'pt_partner_vat_unique_check', 'helpdesk','payment','delivery'],
    'data': [
        'data/ir_cron.xml',
        'views/website_templates.xml',
        'views/website_config_settings.xml',
        'views/delivery_carrier_views.xml',
        'views/payment_method_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'dv_custom_ecommerce/static/src/xml/website_sale_stock_product_availability.xml',
            'dv_custom_ecommerce/static/src/js/website_sale_stock.js',
        ],
    },

    
    'installable': True,
    'application': False,
    'auto_install': False,
}
# en el editor de HTML en direccion de entrega  sustituir con este codigo el selector pais 
# <option t-att-value="c.id" t-att-selected="c.id == (country and country.id) or (not country and c.code == 'GT')">
# para que tome guatemala por defecto siempre
