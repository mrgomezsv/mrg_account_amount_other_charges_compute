# -*- coding: utf-8 -*-
"""Otros Cargos de un documento: la parte del total que no es venta (gravada, exenta o no sujeta) ni IVA.

Para el DTE son (Manual Funcional v2.0, sección XII, y CAT-015):
- Los tributos distintos del IVA (FOVIAL, COTRANS, turismo, específicos...), que Odoo registra como impuestos o,
  en las compras que carga el lector de DTE de proveedores, como líneas sin impuesto con su descripción.
- Los "Cargos/Abonos que no afectan la base imponible" (totalNoGravado del resumen), que los lectores de DTE
  cargan como líneas sin impuesto.

Odoo registra todo eso como impuestos o líneas de la factura, así que ya forma parte de amount_total. Los impuestos
se clasifican con las reglas del motor DTE (mrg_dte_core_sv) y de los libros de IVA (mrg_dte_sv_books) para que
los tres coincidan. Funciones sin dependencia del ORM (reciben registros o cualquier objeto con los mismos
atributos) para poder probarlas sin base de datos; los campos de los módulos DTE se leen solo si existen, porque
este módulo no los requiere.
"""
import json
from collections import Counter

# CAT-015: IVA 13 % (20) e IVA de exportaciones 0 % (C3)
CODIGOS_IVA = ('20', 'C3')
# Retenciones de IVA (CAT-006) con que el motor DTE y los libros reconocen un impuesto de retención
CODIGOS_RETENCION = ('22', 'C4', 'C9')
NOMBRES_TRIBUTO = ('FOVIAL', 'COTRANS')
# Claves con las que el motor y los lectores de DTE pueden envolver el documento guardado en dte_json
CLAVES_DOCUMENTO = ('dteJson', 'dte', 'json', 'documento', 'estructura')
# Montos de venta de un ítem del DTE: un ítem sin ninguno y con noGravado es un cargo/abono que no afecta la base
MONTOS_ITEM = ('ventaNoSuj', 'ventaExenta', 'ventaGravada', 'compra')


def _campo(record, nombre):
    """Valor de un campo que puede no existir en el modelo (False si no existe)."""
    campos = getattr(record, '_fields', None)
    if campos is not None and nombre not in campos:
        return False
    return getattr(record, nombre, False)


def _num(valor):
    try:
        return float(valor or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _nombra_tributo(texto):
    texto = (texto or '').upper()
    return any(nombre in texto for nombre in NOMBRES_TRIBUTO)


def codigo_tributo(tax):
    """Código CAT-015 del impuesto: el de mrg_dte_sv o, si no tiene, el selector de mrg_dte_vendor_reader."""
    tributo = _campo(tax, 'dte_tributo_id')
    codigo = (tributo and tributo.code) or _campo(tax, 'dte_hacienda_tax_code') or ''
    return str(codigo).strip().upper()


def clase_impuesto(tax):
    """Clase fiscal de un impuesto (no grupo): 'iva', 'otro' (tributo distinto del IVA), 'exento' o 'deduccion'
    (retención o percepción de IVA y retención de renta). Son las reglas de clase_impuesto de mrg_dte_sv_books,
    más el nombre FOVIAL/COTRANS que usa el motor DTE y la marca de percepción del lector de proveedores."""
    nombre = (tax.name or '').upper()
    if _nombra_tributo(nombre):
        return 'otro'
    if 'NO SUJ' in nombre or 'EXENT' in nombre:
        return 'exento'
    if tax.amount_type not in ('percent', 'division'):  # 'division' es un porcentaje con el impuesto incluido
        return 'otro'  # importe fijo por unidad (galón, salida del país...): no es IVA ni retención
    codigo = codigo_tributo(tax)
    if (any(texto in nombre for texto in ('RENTA', 'ISR', 'PERC')) or _campo(tax, 'is_iva_percepcion')
            or codigo in CODIGOS_RETENCION or ('RET' in nombre and 'IVA' in nombre) or _num(tax.amount) < 0):
        return 'deduccion'
    if codigo in CODIGOS_IVA:
        return 'iva'
    if codigo:
        return 'otro'  # otro tributo del CAT-015 (turismo, específicos...) aunque sea un porcentaje
    if 'IVA' in nombre or _num(tax.amount) > 0:
        return 'iva'
    return 'exento'  # 0 % sin código


def es_otro_tributo(tax):
    return clase_impuesto(tax) == 'otro'


def _impuestos(taxes):
    """Impuestos de una línea, con cada grupo reemplazado por sus hijos."""
    for tax in taxes or ():
        if tax.amount_type == 'group':
            yield from _impuestos(tax.children_tax_ids)
        else:
            yield tax


def es_linea_sin_tributos(line):
    """Línea de producto sin IVA ni otro tributo (puede llevar retención, percepción o un exento). Así cargan los
    lectores de DTE los cargos que no afectan la base y, en compras, FOVIAL y COTRANS; una línea con su propio
    impuesto de FOVIAL es la base de ese impuesto, que ya se cuenta en su línea de impuesto."""
    return line.display_type == 'product' and not any(
        clase_impuesto(tax) in ('iva', 'otro') for tax in _impuestos(line.tax_ids))


def _cargar(valor):
    if isinstance(valor, str):
        try:
            valor = json.loads(valor)
        except ValueError:
            return None
    return valor if isinstance(valor, dict) else None


def _es_documento(data):
    return isinstance(data, dict) and isinstance(data.get('identificacion'), dict) \
        and isinstance(data.get('resumen'), dict)


def documento_dte(raw):
    """Documento DTE (dict con identificacion y resumen) del texto guardado en dte_json; {} si no se puede leer.
    Acepta el documento directo o envuelto (también como texto JSON), como lo guardan el motor y los lectores de
    DTE; el Evento de Retorno no es un documento de venta. Misma lectura que documento_dte de mrg_dte_sv_books."""
    if not raw:
        return {}
    try:
        data = _cargar(raw) if isinstance(raw, str) else _cargar(dict(raw))
    except (TypeError, ValueError):
        return {}
    if not data:
        return {}
    if not _es_documento(data):
        # Solo se desenvuelve si el contenido es un documento (en el Evento de Retorno 'documento' es el receptor)
        data = next((d for d in (_cargar(data.get(clave)) for clave in CLAVES_DOCUMENTO) if _es_documento(d)), None)
    if not data or (data['identificacion'].get('tipoEvento') and not data['identificacion'].get('tipoDte')):
        return {}
    return data


def nombres_cargos_dte(dte):
    """Descripciones de los cargos de un DTE que el lector de DTE de proveedores carga como líneas sin impuesto:
    los tributos del resumen distintos del IVA (FOVIAL, COTRANS) y los ítems que solo llevan "Cargos/Abonos que no
    afectan la base imponible". Counter: cuántas líneas con esa descripción son cargos."""
    nombres = Counter()
    for tributo in (dte.get('resumen') or {}).get('tributos') or []:
        if isinstance(tributo, dict) and str(tributo.get('codigo') or '').strip().upper() not in CODIGOS_IVA:
            nombres[str(tributo.get('descripcion') or '').strip()] += 1
    for item in dte.get('cuerpoDocumento') or []:
        if isinstance(item, dict) and _num(item.get('noGravado')) and not any(_num(item.get(m)) for m in MONTOS_ITEM):
            nombres[str(item.get('descripcion') or '').strip()] += 1
    nombres.pop('', None)
    return nombres


def otros_cargos(move):
    """Otros cargos del documento en su moneda y con el signo de amount_total (positivo en facturas y notas).

    El signo comercial de cada línea es amount_currency * direction_sign, igual que en el cálculo de amount_total
    de Odoo. Los cargos que no afectan la base se toman de las líneas en compras (el lector de proveedores puede
    cargarlos al 50 % en combustible de persona natural) y del totalNoGravado del DTE en ventas (el motor no los
    emite y el lector de ventas crea una línea "(monto no gravado)" por cada uno, por el mismo monto).
    """
    if not move.is_invoice(include_receipts=True):
        return 0.0
    venta = move.is_sale_document(include_receipts=True)
    dte = documento_dte(_campo(move, 'dte_json'))
    nombres = Counter() if venta else nombres_cargos_dte(dte)
    total = 0.0
    for line in move.line_ids:
        if line.display_type == 'tax':
            if line.tax_line_id and es_otro_tributo(line.tax_line_id):
                total += line.amount_currency * move.direction_sign
        elif es_linea_sin_tributos(line):
            nombre = (line.name or '').strip()
            if nombres[nombre] > 0:
                nombres[nombre] -= 1
            elif not _nombra_tributo(nombre):
                continue
            total += line.amount_currency * move.direction_sign
    if venta:
        total += _num((dte.get('resumen') or {}).get('totalNoGravado'))
    return total
