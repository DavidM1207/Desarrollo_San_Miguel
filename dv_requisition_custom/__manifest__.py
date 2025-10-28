# -*- coding: utf-8 -*-
#-------  -------# 
{   
    'name' : "Personalizacion de Requisiciones",
    'summary': "Modulo de personalizacion para requisiciones",
    'author': "DEValencia",
    'maintainer': 'William Valencia',
    'website': 'https://devalencia.dev',
    'support': 'wvalencia@devalencia.dev', 
    "version": "1.0.0",
    'category': 'Customizations',
    'sequence': 200,
    'depends':['base','base_setup','employee_purchase_requisition','stock'],
    'data':[
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/stock_picking_view.xml',
    ],
    'demo':[],
    'qweb':[],
    'application':True,
    'installable':True,
    'auto_install':False,
}