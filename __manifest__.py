# -*- coding: utf-8 -*-
{
    'name': "sale_purchase_extended",

    'summary': """
        Extend sale_purchase integration""",

    'description': """
        Allways create new PO from new SO
        Generate POs for every product supplier
    """,

    'author': "pmmarquez@gmx.com",

    'category': 'Sales',
    'version': '0.1',
    
    'depends': ['sale_purchase'],

    # always loaded
    # 'data': [
    #     # 'security/ir.model.access.csv',
    #     'views/views.xml',
    #     'views/templates.xml',
    # ],
    # only loaded in demonstration mode
    # 'demo': [
    #     'demo/demo.xml',
    # ],
}
