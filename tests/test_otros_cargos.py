# -*- coding: utf-8 -*-
"""Pruebas de models/otros_cargos.py con objetos simulados (sin base de datos).

Se ejecutan fuera de Odoo con ``python3 -m unittest discover -s tests`` desde la carpeta del módulo. Son
``unittest`` puros: el ejecutor de pruebas de Odoo las omite. otros_cargos.py no define modelos, así que
cargarlo por ruta no interfiere con el registro de Odoo.
"""
import importlib.util
import json
import os
import unittest
from types import SimpleNamespace

try:
    from odoo.addons.mrg_account_amount_other_charges_compute.models import otros_cargos as oc
except ImportError:  # ejecución independiente: Odoo no está o el addon no está en su ruta
    _ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models', 'otros_cargos.py')
    _spec = importlib.util.spec_from_file_location('otros_cargos', _ruta)
    oc = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(oc)

VENTAS = ('out_invoice', 'out_refund', 'out_receipt')
COMPRAS = ('in_invoice', 'in_refund', 'in_receipt')
# direction_sign de Odoo: 1 en asientos y documentos de salida (in_invoice, out_refund, in_receipt), -1 en el resto
SIGNO = {'entry': 1, 'in_invoice': 1, 'out_refund': 1, 'in_receipt': 1,
         'out_invoice': -1, 'in_refund': -1, 'out_receipt': -1}


def impuesto(name, amount, amount_type='percent', codigo=None, selector=None, percepcion=False, hijos=()):
    return SimpleNamespace(
        name=name, amount=amount, amount_type=amount_type, children_tax_ids=list(hijos),
        dte_tributo_id=SimpleNamespace(code=codigo) if codigo else False,
        dte_hacienda_tax_code=selector or False, is_iva_percepcion=percepcion)


def linea_impuesto(tax, monto, move_type):
    """Línea de impuesto con el amount_currency que Odoo le da según el tipo de documento: amount_total es
    direction_sign * suma(amount_currency), así que una factura de cliente lleva sus importes en negativo (haber)."""
    return SimpleNamespace(display_type='tax', name=tax.name, tax_line_id=tax, tax_ids=[],
                           amount_currency=SIGNO[move_type] * monto)


def linea_producto(name, monto, move_type, taxes=()):
    return SimpleNamespace(display_type='product', name=name, tax_line_id=False, tax_ids=list(taxes),
                           amount_currency=SIGNO[move_type] * monto)


def documento(move_type, lineas, dte_json=False):
    return SimpleNamespace(
        move_type=move_type, line_ids=lineas, direction_sign=SIGNO[move_type], dte_json=dte_json,
        is_invoice=lambda include_receipts=False: move_type in VENTAS + COMPRAS,
        is_sale_document=lambda include_receipts=False: move_type in VENTAS)


def dte(tipo='03', resumen=None, cuerpo=None):
    return json.dumps({'identificacion': {'tipoDte': tipo}, 'cuerpoDocumento': cuerpo or [],
                       'resumen': resumen or {}})


IVA = impuesto('IVA 13%', 13.0, codigo='20')
FOVIAL = impuesto('FOVIAL ($0.20 Ctvs. por galón)', 0.20, amount_type='fixed', selector='D1')
COTRANS = impuesto('COTRANS', 0.10, amount_type='fixed')
RETENCION = impuesto('IVA Retenido 1%', -1.0)
PERCEPCION = impuesto('IVA Percibido 1%', 1.0, selector='C3', percepcion=True)
EXENTO = impuesto('Exento', 0.0)


class TestClasificacionImpuestos(unittest.TestCase):

    def test_clases(self):
        casos = [
            (IVA, 'iva'), (impuesto('IVA sin código', 13.0), 'iva'),
            (impuesto('IVA exportación 0%', 0.0, codigo='C3'), 'iva'),
            (impuesto('IVA incluido', 13.0, amount_type='division', codigo='20'), 'iva'),
            (RETENCION, 'deduccion'), (PERCEPCION, 'deduccion'),
            (impuesto('Retención 1%', 1.0, codigo='22'), 'deduccion'),
            (impuesto('Retención 13%', 13.0, selector='C4'), 'deduccion'),
            (impuesto('Percepción especial', 2.0, codigo='D4'), 'deduccion'),
            (impuesto('Impuesto 1% proveedor', 1.0, percepcion=True), 'deduccion'),
            (impuesto('Retención Renta 10%', -10.0), 'deduccion'),
            (EXENTO, 'exento'), (impuesto('No Sujeto', 0.0), 'exento'), (impuesto('Tasa 0%', 0.0), 'exento'),
            (FOVIAL, 'otro'), (COTRANS, 'otro'),
            (impuesto('Fondo vial', 0.20, amount_type='fixed', codigo='D1'), 'otro'),
            (impuesto('FOVIAL (legacy)', 0.20, amount_type='fixed', selector='22'), 'otro'),
            (impuesto('Fovial', 3.0), 'otro'),
            (impuesto('Turismo alojamiento', 5.0, codigo='59'), 'otro'),
            (impuesto('Bebidas', 8.0, selector='D4'), 'otro'),
            (impuesto('Salida del país', 7.0, amount_type='fixed', codigo='71'), 'otro'),
            (impuesto('Tasa por unidad', 0.50, amount_type='fixed'), 'otro'),
        ]
        for tax, clase in casos:
            with self.subTest(tax=tax.name):
                self.assertEqual(oc.clase_impuesto(tax), clase)
                self.assertEqual(oc.es_otro_tributo(tax), clase == 'otro')

    def test_codigo_de_mrg_dte_sv_manda_sobre_el_selector(self):
        self.assertEqual(oc.codigo_tributo(impuesto('X', 1.0, codigo='d1 ', selector='20')), 'D1')
        self.assertEqual(oc.codigo_tributo(impuesto('X', 1.0, selector='C8')), 'C8')
        self.assertEqual(oc.codigo_tributo(impuesto('X', 1.0)), '')

    def test_campos_de_modulos_no_instalados_se_ignoran(self):
        # Registro de Odoo sin los campos DTE: no se leen aunque el objeto tenga el atributo
        tax = impuesto('Turismo', 5.0, codigo='59', percepcion=True)
        tax._fields = {'name': None, 'amount': None, 'amount_type': None}
        self.assertEqual(oc.codigo_tributo(tax), '')
        self.assertEqual(oc.clase_impuesto(tax), 'iva')


class TestLineas(unittest.TestCase):

    def test_lineas_sin_tributos(self):
        for line in (linea_producto('COTRANS ($0.10 Ctvs. por galón)', 1.0, 'in_invoice'),
                     linea_producto('Fovial', 2.0, 'in_invoice', [EXENTO]),
                     linea_producto('Cargo no afecto', 2.0, 'in_invoice', [PERCEPCION, RETENCION])):
            with self.subTest(line=line.name):
                self.assertTrue(oc.es_linea_sin_tributos(line))

    def test_lineas_con_iva_o_tributo(self):
        grupo = impuesto('IVA + Percepción', 0.0, amount_type='group', hijos=[IVA, PERCEPCION])
        for line in (linea_producto('Diesel', 40.0, 'in_invoice', [IVA]),
                     linea_producto('FOVIAL', 2.0, 'in_invoice', [FOVIAL]),
                     linea_producto('Servicio', 10.0, 'in_invoice', [grupo]),
                     linea_impuesto(FOVIAL, 2.0, 'in_invoice')):
            with self.subTest(line=line.name):
                self.assertFalse(oc.es_linea_sin_tributos(line))


class TestDocumentoDte(unittest.TestCase):

    def test_documento_directo_y_envuelto(self):
        doc = json.loads(dte('01', {'totalNoGravado': 2.5}))
        for raw in (json.dumps(doc), json.dumps({'dteJson': doc}), json.dumps({'documento': json.dumps(doc)}), doc):
            with self.subTest(raw=raw):
                self.assertEqual(oc.documento_dte(raw)['resumen']['totalNoGravado'], 2.5)

    def test_sin_documento_o_invalido(self):
        evento = {'identificacion': {'tipoEvento': '18'}, 'documento': {'nombre': 'Cliente'}, 'resumen': {}}
        for raw in (False, '', 'no es json', '[1, 2]', json.dumps({'identificacion': {}}),
                    json.dumps({'dte': 'texto'}), json.dumps(evento)):
            with self.subTest(raw=raw):
                self.assertEqual(oc.documento_dte(raw), {})

    def test_nombres_de_cargos(self):
        doc = json.loads(dte('03', resumen={'tributos': [
            {'codigo': '20', 'descripcion': 'Impuesto al Valor Agregado 13%', 'valor': 5.2},
            {'codigo': 'D1', 'descripcion': 'Fondo vial', 'valor': 2.0},
            {'codigo': 'C8', 'descripcion': '', 'valor': 1.0},
        ]}, cuerpo=[
            {'descripcion': 'Diesel', 'ventaGravada': 40.0, 'noGravado': 0.0},
            {'descripcion': 'Depósito de envase', 'ventaGravada': 0.0, 'noGravado': 3.0},
            {'descripcion': 'Lubricante', 'ventaExenta': 5.0, 'noGravado': 1.0},
        ]))
        self.assertEqual(dict(oc.nombres_cargos_dte(doc)), {'Fondo vial': 1, 'Depósito de envase': 1})
        self.assertEqual(oc.nombres_cargos_dte({}), {})


class TestOtrosCargos(unittest.TestCase):

    def test_compra_de_combustible(self):
        # Diesel 40 + IVA 5.20 + FOVIAL 2.00 (impuesto) + COTRANS 1.00 (línea del lector de proveedores)
        bill = documento('in_invoice', [
            linea_producto('Diesel', 40.0, 'in_invoice', [IVA, FOVIAL]),
            linea_producto('COTRANS ($0.10 Ctvs. por galón)', 1.0, 'in_invoice'),
            linea_impuesto(IVA, 5.20, 'in_invoice'),
            linea_impuesto(FOVIAL, 2.0, 'in_invoice'),
        ])
        self.assertAlmostEqual(oc.otros_cargos(bill), 3.0)

    def test_compra_cargada_por_el_lector_de_proveedores(self):
        # Cargos con la descripción del DTE (al 50 %: persona natural combustible); el exento homónimo no cuenta
        raw = dte('03', resumen={'totalNoGravado': 3.0, 'tributos': [
            {'codigo': '20', 'descripcion': 'IVA 13%', 'valor': 5.2},
            {'codigo': 'D1', 'descripcion': 'Fondo vial', 'valor': 2.0}]}, cuerpo=[
            {'descripcion': 'Diesel', 'ventaGravada': 40.0},
            {'descripcion': 'Depósito', 'noGravado': 3.0},
            {'descripcion': 'Depósito', 'ventaExenta': 4.0}])
        bill = documento('in_invoice', [
            linea_producto('Diesel', 20.0, 'in_invoice', [IVA]),
            linea_producto('Depósito', 1.5, 'in_invoice'),
            linea_producto('Depósito', 2.0, 'in_invoice'),
            linea_producto('Fondo vial', 1.0, 'in_invoice'),
            linea_impuesto(IVA, 2.60, 'in_invoice'),
        ], raw)
        self.assertAlmostEqual(oc.otros_cargos(bill), 2.5)

    def test_signo_positivo_en_todos_los_documentos(self):
        for move_type in VENTAS + COMPRAS:
            with self.subTest(move_type=move_type):
                move = documento(move_type, [
                    linea_producto('Gasolina', 100.0, move_type, [IVA, COTRANS]),
                    linea_producto('Fovial', 2.0, move_type),
                    linea_impuesto(IVA, 13.0, move_type),
                    linea_impuesto(COTRANS, 1.0, move_type),
                    linea_impuesto(RETENCION, -1.0, move_type),
                ])
                self.assertAlmostEqual(oc.otros_cargos(move), 3.0)

    def test_no_gravado_del_dte_en_ventas(self):
        raw = dte('01', resumen={'totalNoGravado': 2.5})
        lineas = [linea_impuesto(FOVIAL, 2.0, 'out_invoice'),
                  linea_producto('Servicio (monto no gravado)', 2.5, 'out_invoice')]
        self.assertAlmostEqual(oc.otros_cargos(documento('out_invoice', lineas, raw)), 4.5)
        # En compras el totalNoGravado no se suma: solo cuentan las líneas que el lector creó para él
        lineas = [linea_impuesto(FOVIAL, 2.0, 'in_invoice')]
        self.assertAlmostEqual(oc.otros_cargos(documento('in_invoice', lineas, raw)), 2.0)

    def test_abono_no_gravado_resta(self):
        raw = dte('03', resumen={'totalNoGravado': -5.0})
        self.assertAlmostEqual(oc.otros_cargos(documento('out_refund', [], raw)), -5.0)

    def test_evento_de_retorno_no_suma(self):
        evento = json.dumps({'identificacion': {'tipoEvento': '18'}, 'resumen': {'totalNoGravado': 9.0}})
        self.assertEqual(oc.otros_cargos(documento('out_refund', [], evento)), 0.0)

    def test_sin_otros_cargos(self):
        move = documento('out_invoice', [linea_producto('Servicio', 100.0, 'out_invoice', [IVA]),
                                         linea_producto('Libro', 20.0, 'out_invoice', [EXENTO]),
                                         linea_impuesto(IVA, 13.0, 'out_invoice')], dte('03'))
        self.assertEqual(oc.otros_cargos(move), 0.0)

    def test_asiento_contable(self):
        move = documento('entry', [linea_impuesto(FOVIAL, 2.0, 'entry')])
        self.assertEqual(oc.otros_cargos(move), 0.0)


if __name__ == '__main__':
    unittest.main()
