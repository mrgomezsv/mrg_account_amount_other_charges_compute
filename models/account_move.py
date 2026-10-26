# -*- coding: utf-8 -*-
from odoo import models, fields, api

from .otros_cargos import otros_cargos


class AccountMove(models.Model):
    _inherit = 'account.move'

    mr_amount_total = fields.Monetary(
        string='Importe Adeudado',
        compute='_compute_mr_cume',
        store=True,
        help='Saldo pendiente de pago del documento (el "Importe adeudado" de Odoo, en la moneda del documento)'
    )

    mr_other_charges = fields.Monetary(
        string='Otros Cargos',
        compute='_compute_mr_cume',
        store=True,
        help='Parte del total que no es venta ni IVA: FOVIAL, COTRANS y demás tributos del CAT-015 distintos del '
             'IVA (como impuestos o como líneas sin impuesto) y los cargos/abonos que no afectan la base imponible '
             'del DTE (totalNoGravado)'
    )

    mr_total_with_other_charges = fields.Monetary(
        string='Total Mas Otros Cargos',
        compute='_compute_mr_cume',
        store=True,
        help='Total del documento: ventas e IVA más los otros cargos, que Odoo ya registra como impuestos o líneas '
             'de la factura'
    )

    def _mr_cume_depends(self):
        depends = ['move_type', 'currency_id', 'amount_total', 'amount_residual',
                   'line_ids.display_type', 'line_ids.name', 'line_ids.amount_currency',
                   'line_ids.tax_ids', 'line_ids.tax_line_id']
        # dte_json lo agrega mrg_dte_sv, que este módulo no requiere
        if 'dte_json' in self._fields:
            depends.append('dte_json')
        return depends

    @api.depends(lambda self: self._mr_cume_depends())
    def _compute_mr_cume(self):
        for move in self:
            other_charges = otros_cargos(move)
            move.mr_other_charges = move.currency_id.round(other_charges) if move.currency_id else other_charges
            # Los otros cargos ya están dentro de amount_total: sumarlos de nuevo los contaría dos veces
            move.mr_total_with_other_charges = move.amount_total
            move.mr_amount_total = move.amount_residual
