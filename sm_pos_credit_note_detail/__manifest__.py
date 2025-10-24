{
    'name': 'Libro Mayor Notas de Crédito',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Point of Sale',
    'summary': 'Libro mayor detallado de notas de crédito por sesión POS',
    'description': """
        Módulo para visualizar notas de crédito de POS de forma detallada
        - Vista de sesiones POS con notas de crédito
        - Vista expandida mostrando cada NC individual
        - Conciliación usando menú Acción nativo de Odoo
    """,
    'author': 'SAN MIGUEL, S.A.',
    
    'depends': [
        'point_of_sale',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/credit_note_line_view.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}