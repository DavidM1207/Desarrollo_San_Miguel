# -*- coding: utf-8 -*-
{
    'name': 'POS Bold Receipt',
    'version': '17.0.1.0.0',
    'category': 'Point of Sale',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_bold_fix/static/src/js/receipt_bold.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}