# -*- coding: utf-8 -*-
{
    'name': 'Tracker - Gestión de Servicios',
    'version': '17.0.1.0.0',
    'category': 'Services',
    'summary': 'Gestión de proyectos y tareas de servicios',
    'description': """
        Sistema de seguimiento de servicios integrado con ventas
    """,
    'author': 'SAN MIGUEL MADERA, S.A.',
    'depends': [
        'base',
        'sale_management',
        'mrp',
        'hr',
        'analytic',
        'account',
    ],
    'data': [
        'security/tracker_security.xml',
        'security/ir.model.access.csv',
        'data/tracker_data.xml',
        'views/tracker_menus.xml',
        'views/tracker_project_views.xml',
        'views/tracker_task_views.xml',
        'views/tracker_timesheet_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}