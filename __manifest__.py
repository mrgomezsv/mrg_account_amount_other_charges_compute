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
    'version': '0.1',

    'depends': ['base', 'account'],

    'data': [
        'views/account_move.xml',
    ],
}
