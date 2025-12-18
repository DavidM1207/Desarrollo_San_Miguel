# -*- coding: utf-8 -*-
{
    'name': 'POS Bold Receipt',
    'version': '17.0.1.0.0',
    'category': 'Point of Sale',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_bold_final/static/src/js/receipt_bold.js',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}