# -*- coding: utf-8 -*-
import logging

from odoo import api, SUPERUSER_ID
from odoo.tools import split_every

_logger = logging.getLogger(__name__)

CAMPOS = ('mr_amount_total', 'mr_other_charges', 'mr_total_with_other_charges')


def migrate(cr, version):
    """Importe Adeudado pasa a ser el saldo pendiente (antes copiaba el total) y Otros Cargos se calcula de los
    impuestos y líneas de la factura (antes leía un campo que no existe y siempre daba 0). Odoo no recalcula los
    campos almacenados al actualizar el módulo, así que se recalculan aquí."""
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.flush_all()
    # Saldo y total se copian por SQL en todos los asientos; los otros cargos solo existen en facturas
    cr.execute("""
        UPDATE account_move
           SET mr_amount_total = COALESCE(amount_residual, 0),
               mr_total_with_other_charges = COALESCE(amount_total, 0),
               mr_other_charges = 0
    """)
    env.invalidate_all()

    Move = env['account.move']
    campos = [Move._fields[nombre] for nombre in CAMPOS]
    ids = Move.search([('move_type', 'in', Move.get_invoice_types(include_receipts=True))]).ids
    # Por lotes, para no cargar todas las facturas en memoria
    for lote in split_every(1000, ids):
        moves = Move.browse(lote)
        for campo in campos:
            env.add_to_compute(campo, moves)
        # Calcula y guarda el lote, y libera la caché antes del siguiente
        env.invalidate_all()
    _logger.info("mrg_account_amount_other_charges_compute: importe adeudado y total copiados en todos los asientos; "
                 "otros cargos recalculados en %s factura(s)", len(ids))
