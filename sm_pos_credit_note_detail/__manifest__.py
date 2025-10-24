{
    'name': 'Libro Mayor Notas de Crédito',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Point of Sale',
    'summary': 'Libro mayor detallado de notas de crédito por sesión POS con vista expandida',
    'description': """
        Módulo para visualizar notas de crédito de POS de forma detallada
        - Vista de sesiones POS con notas de crédito
        - Vista expandida mostrando cada NC individual
        - Identificación de NC originales vs refacturaciones
        - Conciliación directa desde vista expandida
    """,
    'author': 'SAN MIGUEL, S.A.',
     
    'depends': [
        'base',
        'point_of_sale',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/credit_note_line_view.xml',
        'views/credit_note_detail_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}