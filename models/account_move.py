# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    mr_amount_total = fields.Monetary(
        string='Importe Adeudado',
        compute='_compute_mr_cume',
        store=True,
        help='Muestra solo el valor del Importe Adeudado'
    )

    mr_other_charges = fields.Monetary(
        string='Otros Cargos',
        compute='_compute_mr_cume',
        store=True,
        help='Muestra solo el valor de Otros Cargos'
    )

    mr_total_with_other_charges = fields.Monetary(
        string='Total Mas Otros Cargos',
        compute='_compute_mr_cume',
        store=True,
        help='Muestra el valor del Total Mas Otros Cargos'
    )

    @api.depends('amount_total', 'dte_other_charges_tr_ids', 'dte_other_charges_tr_ids.amount')
    def _compute_mr_cume(self):
        for move in self:
            other_charges = sum(move.dte_other_charges_tr_ids.mapped('amount'))
            mr_total = other_charges + move.amount_total
            move.mr_total_with_other_charges = mr_total
            move.mr_other_charges = other_charges
            move.mr_amount_total = move.amount_total
