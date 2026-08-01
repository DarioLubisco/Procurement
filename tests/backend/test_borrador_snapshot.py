from analytics_engine.core.borrador_snapshot import (
    build_desviacion_rows,
    count_desviaciones,
    filter_comparativa_for_barras,
    filter_propuesto_for_cod_prov,
    snapshot_hash,
)


def test_count_desviaciones_qty_and_sucedaneo_and_alta():
    comp = [
        {"barra_baseline": "A", "barra_propuesto": "A", "qty_baseline": 10, "qty_propuesto": 10},
        {"barra_baseline": "B", "barra_propuesto": "B", "qty_baseline": 5, "qty_propuesto": 8},
        {"barra_baseline": "C", "barra_propuesto": "D", "qty_baseline": 1, "qty_propuesto": 1},
        {"barra_baseline": "", "barra_propuesto": "E", "qty_baseline": 0, "qty_propuesto": 2},
    ]
    assert count_desviaciones(comp) == 3
    assert len(build_desviacion_rows(comp)) == 3


def test_snapshot_hash_stable():
    a = snapshot_hash([{"x": 1}], [{"barra": "1"}])
    b = snapshot_hash([{"x": 1}], [{"barra": "1"}])
    assert a == b and len(a) == 64


def test_filters():
    prop = filter_propuesto_for_cod_prov(
        [{"barra": "1", "proveedor": "ZAKI"}, {"barra": "2", "proveedor": "OTHER"}],
        "ZAKI",
    )
    assert len(prop) == 1
    comp = filter_comparativa_for_barras(
        [
            {"barra_propuesto": "1", "qty_propuesto": 1},
            {"barra_propuesto": "9", "qty_propuesto": 1},
        ],
        ["1"],
    )
    assert len(comp) == 1
