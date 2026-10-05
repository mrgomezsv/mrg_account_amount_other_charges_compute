# -*- coding: utf-8 -*-
{
    'name': "Account Amount Other Charges Compute",

    'summary': """
        Módulo para mostrar monto residual en vista de lista en el campo Otros Cargos""",

    'description': """
        Este módulo agrega el campo mr_cume en la vista de lista de facturas
    """,

    'author': "Mario Roberto",
    'website': "https://mrgomezsv.github.io/",

    'category': 'Accounting/Accounting',
    'version': '20.0.1.0.0',
    'license': 'LGPL-3',

    'depends': ['base', 'account'],

    'data': [
        'views/account_move.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
