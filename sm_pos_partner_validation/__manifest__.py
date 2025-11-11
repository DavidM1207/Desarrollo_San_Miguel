# -*- coding: utf-8 -*-
{
    'name': 'POS Partner Phone Validation',
    'version': '17.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Campos de teléfono obligatorios al crear/editar clientes en POS',
    'description': """
        Validación de Clientes en POS
        ==============================
        * Hace obligatorio el campo Mobile (Móvil)
        * Hace obligatorio el campo Phone (Teléfono)
        * Valida antes de guardar
        * Muestra mensaje de error claro
    """,
    'author': 'SAN MIGUEL MADERA, S.A.',

    'depends': ['point_of_sale'],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'sm_pos_partner_validation/static/src/js/partner_editor.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}