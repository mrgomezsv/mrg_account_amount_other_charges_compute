# -*- coding: utf-8 -*-
{
    'name': "Account Amount Other Charges Compute",

    'summary': """
        Importe adeudado, otros cargos y total con otros cargos en la lista de facturas""",

    'description': """
        Agrega a la lista de facturas (columnas opcionales, con totales al agrupar):

        - Importe Adeudado: saldo pendiente de pago del documento.
        - Otros Cargos: parte del total que no es venta ni IVA. FOVIAL, COTRANS y demás tributos del
          CAT-015 distintos del IVA (impuestos clasificados con las reglas del motor DTE y los libros de
          IVA; también las líneas sin impuesto de FOVIAL/COTRANS) y los cargos/abonos que no afectan la
          base imponible (totalNoGravado del DTE en ventas; en compras, las líneas que el lector de DTE
          de proveedores crea para ellos).
        - Total Mas Otros Cargos: total del documento, que ya incluye los otros cargos.

        Los tres campos van en la moneda del documento y en positivo en facturas y notas de crédito.
    """,

    'author': "Mario Roberto",
    'website': "https://mrgomezsv.github.io/",

    'category': 'Accounting/Accounting',
    'version': '20.0.1.1.0',
    'license': 'LGPL-3',

    'depends': ['base', 'account'],

    'data': [
        'views/account_move.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
