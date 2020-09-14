# -*- coding: utf-8 -*-
{
    'name': "sale_purchase_extended",

    'summary': """
        Extend sale_purchase integration""",

    'description': """
        -Allways create new PO from new SO
        -Generate POs for every product supplier
        -Cancel POs related with SO when SO is canceled
        -When one PO is confirmed cancel other orders related to same SO and new PO lines are copied to SO
        -When PO state to sent add origin SO client and PO supplier to followers
        -create_full_invoice method to generate Invoice from SO
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
