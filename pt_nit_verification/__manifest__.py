# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################
{
    'name': 'NIT Verification',
    'summary': 'Verifica el NIT del contacto desde punto de venta',
    'version': '1.0',
    'description': """Verificación de NIT desde punto de venta""",
    'author': 'Pitaya Tech',
    'category': 'Website',
    'website': "http://www.pitayatech.com",
    'depends': ['base_setup', 'base', 'account', 'pt_multicert_felgt'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/res_config_settings_view.xml',
        'wizzard/massive_nit_update_views.xml'
    ],
    'images': ['static/description/logo.png'],
    'installable': True,
    'auto_install': False,
    'assets': {
        'point_of_sale.assets': [
            'pt_nit_verification/static/src/js/ClientDetailEdit.js'
        ],
    },
    'license': 'Other proprietary',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
