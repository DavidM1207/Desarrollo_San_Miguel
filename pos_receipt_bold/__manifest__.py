# -*- coding: utf-8 -*-
{
    'name': 'POS Receipt Bold Fields',
    'version': '17.0.1.0.0',
    'category': 'Point of Sale',
    'depends': ['point_of_sale', 'pt_mock_up_pos_receipt'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_receipt_bold/static/src/xml/receipt_bold.xml',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}