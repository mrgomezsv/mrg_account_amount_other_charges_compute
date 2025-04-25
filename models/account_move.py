# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    mr_total_with_other_charges = fields.Monetary(
        string='Otros Cargos',
        compute='_compute_mr_cume',
        help='Muestra el valor del monto total'
    )

    @api.depends('amount_total')
    def _compute_mr_cume(self):
        for move in self:
            other_charges = sum(move.dte_other_charges_tr_ids.mapped('amount'))
            mr_total = other_charges + move.amount_total
            move.mr_total_with_other_charges = mr_total
