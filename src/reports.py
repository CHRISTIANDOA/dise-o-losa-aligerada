from __future__ import annotations

from io import BytesIO, StringIO

import ezdxf
import xlsxwriter

from .models import DesignResult


def build_excel_report(result: DesignResult) -> bytes:
    stream = BytesIO()
    workbook = xlsxwriter.Workbook(stream, {"in_memory": True})
    workbook.set_properties({"title": "Memoria de cálculo de losa aligerada", "author": "Christiand Olórtegui Artica"})
    title = workbook.add_format({"bold": True, "font_size": 16, "font_color": "#FFFFFF", "bg_color": "#17365D", "align": "center", "valign": "vcenter"})
    section = workbook.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": "#4F81BD", "border": 1})
    header = workbook.add_format({"bold": True, "bg_color": "#D9EAF7", "border": 1, "text_wrap": True, "align": "center", "valign": "vcenter"})
    cell = workbook.add_format({"border": 1, "valign": "top"})
    number = workbook.add_format({"border": 1, "num_format": "0.000", "valign": "top"})
    ok = workbook.add_format({"border": 1, "bg_color": "#C6EFCE", "font_color": "#006100", "bold": True, "align": "center"})
    bad = workbook.add_format({"border": 1, "bg_color": "#FFC7CE", "font_color": "#9C0006", "bold": True, "align": "center"})
    note = workbook.add_format({"italic": True, "font_color": "#666666", "text_wrap": True})

    summary = workbook.add_worksheet("Resumen")
    summary.hide_gridlines(2)
    summary.set_landscape()
    summary.fit_to_pages(1, 1)
    summary.set_column("A:A", 30)
    summary.set_column("B:B", 20)
    summary.set_column("C:D", 34)
    summary.merge_range("A1:D2", "MEMORIA DE CÁLCULO - LOSA ALIGERADA UNIDIRECCIONAL", title)
    summary.write("A4", "Resultado general", section)
    summary.write("B4", result.overall_status, ok if result.overall_status == "CUMPLE" else bad)
    rows = [
        ("Espesor seleccionado", result.selected_height_cm, "cm", "E.060, Tabla 9.1"),
        ("Peralte efectivo", result.effective_depth_cm, "cm", "Hipótesis geométrica"),
        ("Carga muerta", result.dead_load_kg_m2, "kgf/m²", "E.020"),
        ("Carga última superficial", result.factored_load_kg_m2, "kgf/m²", "E.060, 9.2.1"),
        ("Carga última por vigueta", result.factored_line_load_t_m, "tf/m", "Ancho tributario"),
        ("Cortante máximo", result.vu_max_tf, "tf", "E.060, 8.3.4"),
        ("Resistencia de diseño a cortante", result.phi_vc_tf, "tf", "E.060, 8.11.8 y Cap. 11"),
        ("Acero de temperatura", result.temperature_as_cm2_m, "cm²/m", "E.060, 9.7"),
        ("Espaciamiento de temperatura", result.temperature_spacing_cm, "cm", f"{result.temperature_bar_label}"),
    ]
    summary.write_row("A6", ["Magnitud", "Resultado", "Unidad", "Referencia"], header)
    for index, row in enumerate(rows, 6):
        summary.write(index, 0, row[0], cell)
        summary.write_number(index, 1, row[1], number)
        summary.write(index, 2, row[2], cell)
        summary.write(index, 3, row[3], cell)
    summary.write("A17", "Advertencias", section)
    if result.warnings:
        for index, warning in enumerate(result.warnings, 17):
            summary.merge_range(index, 0, index, 3, warning, note)
    else:
        summary.merge_range("A18:D18", "No se generaron advertencias para los datos ingresados.", note)

    data = workbook.add_worksheet("Datos")
    data.hide_gridlines(2)
    data.set_column("A:A", 34)
    data.set_column("B:B", 18)
    data.set_column("C:C", 18)
    data.merge_range("A1:C2", "DATOS DE ENTRADA", title)
    data.write_row("A4", ["Dato", "Valor", "Unidad"], header)
    input_rows = [
        ("Luces", " - ".join(f"{x:.2f}" for x in result.inputs.spans_m), "m"),
        ("Resistencia del concreto f'c", result.inputs.fc_kg_cm2, "kgf/cm²"),
        ("Fluencia del acero fy", result.inputs.fy_kg_cm2, "kgf/cm²"),
        ("Ancho del nervio bw", result.inputs.rib_width_cm, "cm"),
        ("Separación entre ejes", result.inputs.rib_spacing_cm, "cm"),
        ("Espesor de losa superior", result.inputs.topping_cm, "cm"),
        ("Recubrimiento", result.inputs.cover_cm, "cm"),
        ("Acabados", result.inputs.finishes_kg_m2, "kgf/m²"),
        ("Tabiquería", result.inputs.partitions_kg_m2, "kgf/m²"),
        ("Carga viva", result.inputs.live_load_kg_m2, "kgf/m²"),
        ("Apoyo exterior", result.inputs.outer_support, ""),
        ("Longitud recta disponible", result.inputs.available_anchor_cm, "cm"),
    ]
    for index, row in enumerate(input_rows, 4):
        data.write(index, 0, row[0], cell)
        if isinstance(row[1], (int, float)):
            data.write_number(index, 1, row[1], number)
        else:
            data.write(index, 1, row[1], cell)
        data.write(index, 2, row[2], cell)
    data.write("A19", "Fuentes", section)
    data.merge_range("A20:C20", "Norma E.020 Cargas: peso propio y carga viva. Norma E.060 Concreto Armado: análisis, resistencia, losas nervadas, cortante y desarrollo.", note)

    calc = workbook.add_worksheet("Cálculos")
    calc.hide_gridlines(2)
    calc.set_landscape()
    calc.fit_to_pages(1, 0)
    widths = [25, 13, 12, 13, 13, 15, 18, 18, 15, 13, 14, 23, 12]
    for col, width in enumerate(widths):
        calc.set_column(col, col, width)
    calc.merge_range(0, 0, 1, 12, "DISEÑO POR FLEXIÓN", title)
    headers = ["Sección", "Tipo", "Coef.", "L (m)", "b (cm)", "Mu (tf·m)", "As calc. (cm²)", "4/3 As (cm²)", "Refuerzo", "As prov. (cm²)", "εt", "Modelo", "Estado"]
    calc.write_row(3, 0, headers, header)
    for row_index, item in enumerate(result.flexure, 4):
        values = [item.location, item.kind, item.coefficient, item.length_m, item.width_cm, item.mu_tfm, item.as_calc_cm2, item.as_target_cm2, item.bar_label, item.as_provided_cm2, item.tensile_strain, item.section_model]
        for col, value in enumerate(values):
            if isinstance(value, (int, float)):
                calc.write_number(row_index, col, value, number)
            else:
                calc.write(row_index, col, value, cell)
        calc.write(row_index, 12, item.status, ok if item.status == "CUMPLE" else bad)

    start = 6 + len(result.flexure)
    calc.write(start, 0, "TRAZABILIDAD DE FÓRMULAS", section)
    calc.write_row(start + 1, 0, ["Cálculo", "Ecuación", "Sustitución", "Resultado", "Referencia"], header)
    trace = [
        ("Carga muerta", "CM = PP + acabados + tabiquería", f"CM = {result.dead_load_kg_m2-result.inputs.finishes_kg_m2-result.inputs.partitions_kg_m2:.1f} + {result.inputs.finishes_kg_m2:.1f} + {result.inputs.partitions_kg_m2:.1f}", f"{result.dead_load_kg_m2:.1f} kgf/m²", "E.020"),
        ("Carga última", "wu = 1,4CM + 1,7CV", f"wu = 1,4({result.dead_load_kg_m2:.1f}) + 1,7({result.inputs.live_load_kg_m2:.1f})", f"{result.factored_load_kg_m2:.1f} kgf/m²", "E.060 9.2.1"),
        ("Carga por vigueta", "wu,v = wu·s", f"wu,v = {result.factored_load_kg_m2:.1f}({result.inputs.rib_spacing_cm/100:.2f})", f"{result.factored_line_load_t_m:.4f} tf/m", "Ancho tributario"),
        ("Cortante", "φVc = 0,85(1,10)(0,53√f'c bw d)", f"φVc = 0,85(1,10)(0,53√{result.inputs.fc_kg_cm2:.0f})({result.inputs.rib_width_cm:.1f})({result.effective_depth_cm:.1f})", f"{result.phi_vc_tf:.3f} tf", "E.060 8.11.8, 11.3 y 9.3.2.3"),
        ("Temperatura", "Ast = 0,0018(100)hf", f"Ast = 0,0018(100)({result.inputs.topping_cm:.1f})", f"{result.temperature_as_cm2_m:.3f} cm²/m", "E.060 9.7"),
    ]
    for index, row in enumerate(trace, start + 2):
        for col, value in enumerate(row):
            calc.write(index, col, value, cell)

    development = workbook.add_worksheet("Desarrollo")
    development.hide_gridlines(2)
    development.set_column("A:A", 18)
    development.set_column("B:E", 22)
    development.merge_range("A1:E2", "LONGITUD DE DESARROLLO Y ANCLAJE", title)
    development.write_row("A4", ["Barra", "ld recta (cm)", "ld gancho base (cm)", "Disponible (cm)", "Estado"], header)
    for index, item in enumerate(result.development, 4):
        development.write(index, 0, item.bar_label, cell)
        development.write_number(index, 1, item.ld_cm, number)
        development.write_number(index, 2, item.ldh_cm, number)
        development.write_number(index, 3, item.available_cm, number)
        development.write(index, 4, item.straight_status, ok if item.straight_status == "CUMPLE" else bad)
    note_row = 5 + len(result.development) + 1
    development.merge_range(note_row, 0, note_row + 1, 4, "La longitud con gancho se presenta sin reducciones adicionales por recubrimiento o confinamiento. El detallado definitivo debe comprobar la geometría real del apoyo y los requisitos del numeral 12.5.", note)

    workbook.close()
    return stream.getvalue()


def _add_rect(msp, x, y, width, height, layer):
    points = [(x, y), (x + width, y), (x + width, y + height), (x, y + height), (x, y)]
    msp.add_lwpolyline(points, dxfattribs={"layer": layer})


def build_dxf(result: DesignResult) -> bytes:
    document = ezdxf.new("R2010")
    document.units = ezdxf.units.MM
    for name, color in [("CONCRETO", 8), ("ALIGERADO", 30), ("ACERO_POS", 5), ("ACERO_NEG", 1), ("ACERO_TEMP", 3), ("COTAS", 7), ("TEXTOS", 7)]:
        document.layers.add(name, color=color)
    msp = document.modelspace()
    h = result.selected_height_cm * 10.0
    hf = result.inputs.topping_cm * 10.0
    pitch = result.inputs.rib_spacing_cm * 10.0
    bw = result.inputs.rib_width_cm * 10.0
    cover = result.inputs.cover_cm * 10.0
    bays = 3
    total = bays * pitch
    critical_positive = max((item for item in result.flexure if item.kind == "Positivo"), key=lambda item: item.mu_tfm)
    bar_count = int(critical_positive.bar_label.split()[0])
    bar_radius = critical_positive.bar_diameter_mm / 2.0

    _add_rect(msp, 0, 0, total, hf, "CONCRETO")
    for index in range(bays):
        center = pitch * (index + 0.5)
        _add_rect(msp, center - bw / 2.0, -h + hf, bw, h - hf, "CONCRETO")
        offsets = [0.0] if bar_count == 1 else [-(bar_radius + 2.5), bar_radius + 2.5]
        for offset in offsets:
            msp.add_circle((center + offset, -h + cover + bar_radius), bar_radius, dxfattribs={"layer": "ACERO_POS"})
        if index < bays - 1:
            _add_rect(msp, center + bw / 2.0, -h + hf + 10.0, pitch - bw, h - hf - 10.0, "ALIGERADO")
    x = result.temperature_spacing_cm * 10.0 / 2.0
    while x < total:
        msp.add_circle((x, -cover), result.inputs.temperature_bar_mm / 2.0, dxfattribs={"layer": "ACERO_TEMP"})
        x += result.temperature_spacing_cm * 10.0
    msp.add_text("SECCION TRANSVERSAL - LOSA ALIGERADA", height=35, dxfattribs={"layer": "TEXTOS"}).set_placement((0, 70))
    msp.add_text(f"h={result.selected_height_cm:.0f} cm | hf={result.inputs.topping_cm:.0f} cm | bw={result.inputs.rib_width_cm:.0f} cm | s={result.inputs.rib_spacing_cm:.0f} cm", height=22, dxfattribs={"layer": "TEXTOS"}).set_placement((0, 35))
    msp.add_text(f"Temperatura: {result.temperature_bar_label} @ {result.temperature_spacing_cm:.0f} cm", height=22, dxfattribs={"layer": "TEXTOS"}).set_placement((0, -h - 45))
    msp.add_text(f"Acero positivo mostrado: {critical_positive.bar_label}", height=22, dxfattribs={"layer": "TEXTOS"}).set_placement((total * 0.52, -h - 45))

    y0 = -h - 260.0
    scale = 250.0
    x0 = 0.0
    msp.add_text("ELEVACION ESQUEMATICA DE VIGUETA", height=35, dxfattribs={"layer": "TEXTOS"}).set_placement((x0, y0 + 110))
    cursor = x0
    for index, span in enumerate(result.inputs.spans_m):
        span_mm = span * scale
        msp.add_line((cursor, y0), (cursor + span_mm, y0), dxfattribs={"layer": "CONCRETO"})
        msp.add_line((cursor, y0 - 25), (cursor + span_mm, y0 - 25), dxfattribs={"layer": "ACERO_POS"})
        msp.add_text(f"L{index+1}={span:.2f} m", height=18, dxfattribs={"layer": "COTAS"}).set_placement((cursor + span_mm * 0.38, y0 - 65))
        _add_rect(msp, cursor - 12, y0 - 55, 24, 110, "CONCRETO")
        cursor += span_mm
    _add_rect(msp, cursor - 12, y0 - 55, 24, 110, "CONCRETO")
    for support in range(1, len(result.inputs.spans_m)):
        support_x = x0 + sum(result.inputs.spans_m[:support]) * scale
        extension = max((item.ld_cm for item in result.development), default=30.0) * 2.5
        msp.add_line((support_x - extension, y0 + 25), (support_x + extension, y0 + 25), dxfattribs={"layer": "ACERO_NEG"})
    msp.add_text("ESQUEMA REFERENCIAL: completar cortes y anclajes con el plano estructural definitivo.", height=18, dxfattribs={"layer": "TEXTOS"}).set_placement((x0, y0 - 105))

    output = StringIO()
    document.write(output, fmt="asc")
    return output.getvalue().encode("utf-8")
