from __future__ import annotations

import streamlit as st

from src.design import design_slab
from src.models import SlabInputs
from src.reports import build_dxf, build_excel_report
from src.visuals import section_figure


st.set_page_config(page_title="Diseño de losa aligerada E.060", page_icon="🏗️", layout="wide")
st.title("Diseño de losa aligerada unidireccional")
st.caption("Procedimiento basado en las normas peruanas E.020 y E.060. Unidades de entrada: kgf, cm y m.")

with st.sidebar:
    st.header("Datos del proyecto")
    number_spans = st.number_input("Número de tramos", min_value=2, max_value=5, value=3, step=1)
    spans = []
    for index in range(int(number_spans)):
        spans.append(st.number_input(f"Luz libre del tramo {index + 1} (m)", min_value=1.0, max_value=12.0, value=3.0, step=0.05))
    outer_support = st.selectbox("Apoyo exterior", ["Viga de borde", "Columna", "No restringido"])

    st.subheader("Materiales")
    fc = st.number_input("f'c (kgf/cm²)", min_value=175.0, max_value=700.0, value=210.0, step=5.0)
    fy = st.number_input("fy (kgf/cm²)", min_value=2800.0, max_value=5500.0, value=4200.0, step=100.0)

    st.subheader("Geometría")
    rib_width = st.number_input("Ancho del nervio (cm)", min_value=8.0, max_value=30.0, value=10.0, step=1.0)
    spacing = st.number_input("Separación entre ejes (cm)", min_value=25.0, max_value=85.0, value=40.0, step=1.0)
    topping = st.number_input("Espesor de losa superior (cm)", min_value=4.0, max_value=12.0, value=5.0, step=0.5)
    cover = st.number_input("Recubrimiento (cm)", min_value=1.5, max_value=7.0, value=2.0, step=0.25)
    use_manual_height = st.checkbox("Definir altura manualmente")
    manual_height = st.number_input("Altura total (cm)", min_value=12.0, max_value=60.0, value=17.0, step=1.0, disabled=not use_manual_height)

    st.subheader("Cargas")
    auto_self_weight = st.checkbox("Obtener peso propio de la E.020", value=True)
    self_weight = st.number_input("Peso propio (kgf/m²)", min_value=0.0, value=280.0, step=10.0, disabled=auto_self_weight)
    finishes = st.number_input("Acabados (kgf/m²)", min_value=0.0, value=100.0, step=10.0)
    partitions = st.number_input("Tabiquería (kgf/m²)", min_value=0.0, value=150.0, step=10.0)
    live_load = st.number_input("Carga viva (kgf/m²)", min_value=0.0, value=200.0, step=10.0)

    st.subheader("Anclaje")
    available_anchor = st.number_input("Longitud recta disponible (cm)", min_value=5.0, value=45.0, step=5.0)

inputs = SlabInputs(
    spans_m=tuple(spans), fc_kg_cm2=fc, fy_kg_cm2=fy, rib_width_cm=rib_width,
    rib_spacing_cm=spacing, topping_cm=topping, cover_cm=cover,
    manual_height_cm=manual_height if use_manual_height else None,
    slab_self_weight_kg_m2=None if auto_self_weight else self_weight,
    finishes_kg_m2=finishes, partitions_kg_m2=partitions,
    live_load_kg_m2=live_load, outer_support=outer_support,
    available_anchor_cm=available_anchor,
)

try:
    result = design_slab(inputs)
except ValueError as exc:
    st.error(str(exc))
    st.stop()

metric_cols = st.columns(5)
metric_cols[0].metric("Altura seleccionada", f"{result.selected_height_cm:.0f} cm", f"requerida {result.required_height_cm:.2f} cm")
metric_cols[1].metric("Carga última", f"{result.factored_load_kg_m2:.1f} kgf/m²")
metric_cols[2].metric("Carga por vigueta", f"{result.factored_line_load_t_m:.4f} tf/m")
metric_cols[3].metric("Cortante", result.shear_status, f"φVc = {result.phi_vc_tf:.3f} tf")
metric_cols[4].metric("Resultado", result.overall_status)

if result.warnings:
    for warning in result.warnings:
        st.warning(warning)

tab_summary, tab_flexure, tab_checks, tab_downloads = st.tabs(["Sección", "Flexión", "Verificaciones", "Descargas"])

with tab_summary:
    left, right = st.columns([1.7, 1])
    with left:
        st.pyplot(section_figure(result), use_container_width=True)
    with right:
        st.subheader("Refuerzo transversal")
        st.write(f"**{result.temperature_bar_label} @ {result.temperature_spacing_cm:.0f} cm**")
        st.write(f"Área requerida: {result.temperature_as_cm2_m:.3f} cm²/m")
        st.subheader("Cortante")
        st.write(f"Vu máximo = {result.vu_max_tf:.3f} tf")
        st.write(f"Vc de la nervadura = {result.vc_tf:.3f} tf")
        st.write(f"φVc = {result.phi_vc_tf:.3f} tf")

with tab_flexure:
    table = []
    for item in result.flexure:
        table.append({
            "Sección": item.location, "Tipo": item.kind, "Coef.": round(item.coefficient, 4),
            "Mu (tf·m)": round(item.mu_tfm, 4), "As calculada (cm²)": round(item.as_calc_cm2, 3),
            "4/3 As (cm²)": round(item.as_target_cm2, 3), "Refuerzo": item.bar_label,
            "As provista (cm²)": round(item.as_provided_cm2, 3), "εt": round(item.tensile_strain, 5),
            "φMn (tf·m)": round(item.phi_mn_tfm, 4), "Modelo": item.section_model, "Estado": item.status,
        })
    st.dataframe(table, use_container_width=True, hide_index=True)
    st.caption("La selección usa la ruta simplificada del numeral 10.5.3: As provista ≥ 4/3 As requerida.")

with tab_checks:
    st.subheader("Aplicabilidad del método aproximado")
    st.dataframe([{"Verificación": a, "Comprobación": b, "Estado": c} for a, b, c in result.method_checks], use_container_width=True, hide_index=True)
    st.subheader("Geometría de losa nervada")
    st.dataframe([{"Verificación": a, "Comprobación": b, "Estado": c} for a, b, c in result.geometry_checks], use_container_width=True, hide_index=True)
    st.subheader("Longitud de desarrollo")
    st.dataframe([{
        "Barra": item.bar_label, "ld recta (cm)": round(item.ld_cm, 1),
        "ld con gancho base (cm)": round(item.ldh_cm, 1), "Disponible (cm)": item.available_cm,
        "Estado": item.straight_status,
    } for item in result.development], use_container_width=True, hide_index=True)
    st.caption("El gancho se presenta sin reducciones por confinamiento. El detalle definitivo debe revisar E.060 12.5.")

with tab_downloads:
    st.write("Los archivos se generan con los mismos datos y resultados mostrados en pantalla.")
    excel_bytes = build_excel_report(result)
    dxf_bytes = build_dxf(result)
    col1, col2 = st.columns(2)
    col1.download_button("Descargar memoria Excel", excel_bytes, "memoria_losa_aligerada.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    col2.download_button("Descargar detalle DXF", dxf_bytes, "detalle_losa_aligerada.dxf", "application/dxf", use_container_width=True)
    st.info("El DXF contiene una sección transversal y una elevación esquemática. El plano constructivo definitivo debe completar cortes, anclajes y notas del proyecto.")

st.divider()
st.caption("Base normativa: RNE E.020 Cargas y RNE E.060 Concreto Armado. La herramienta sirve para cálculo académico y requiere revisión del ingeniero responsable antes de uso profesional.")

