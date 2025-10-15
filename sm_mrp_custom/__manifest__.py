# -*- coding: utf-8 -*-
#-------  -------# 
{   
    'name' : "Personalizacion MRP",
    'summary': "Modulo de personalizacion para MRP",
    'author': "San Miguel",
    "version": "1.0.0",
    'category': 'Report',
    'sequence': 200,
    'depends':['base','base_setup','mrp'],
    'data':[
        'security/ir.model.access.csv',
        'wizard/mrp_custom_fabric.xml',
    ],
    'demo':[],
    'qweb':[],
    'application':True,
    'installable':True,
    'auto_install':False,
}