from __future__ import annotations

import math
from dataclasses import replace

from .models import DesignResult, DevelopmentResult, FlexureResult, SlabInputs


KGCM2_TO_MPA = 0.0980665
PHI_FLEXURE = 0.90
PHI_SHEAR = 0.85
STANDARD_HEIGHTS_CM = (17.0, 20.0, 25.0, 30.0)
BAR_OPTIONS = (
    ("Ø 1/4\"", 6.35),
    ("Ø 3/8\"", 9.525),
    ("Ø 1/2\"", 12.70),
    ("Ø 5/8\"", 15.875),
    ("Ø 3/4\"", 19.05),
    ("Ø 1\"", 25.40),
)


def bar_area_cm2(diameter_mm: float) -> float:
    diameter_cm = diameter_mm / 10.0
    return math.pi * diameter_cm**2 / 4.0


def default_self_weight(height_cm: float) -> float:
    table = {17.0: 280.0, 20.0: 300.0, 25.0: 350.0, 30.0: 420.0}
    if height_cm in table:
        return table[height_cm]
    keys = sorted(table)
    if height_cm <= keys[0]:
        return table[keys[0]]
    if height_cm >= keys[-1]:
        return table[keys[-1]]
    for low, high in zip(keys, keys[1:]):
        if low <= height_cm <= high:
            ratio = (height_cm - low) / (high - low)
            return table[low] + ratio * (table[high] - table[low])
    raise ValueError("No se pudo determinar el peso propio.")


def _required_height(spans_m: tuple[float, ...]) -> tuple[float, list[float]]:
    required = []
    last = len(spans_m) - 1
    for index, span in enumerate(spans_m):
        divisor = 18.5 if index in (0, last) else 21.0
        required.append(span * 100.0 / divisor)
    return max(required), required


def _select_height(required_cm: float) -> float:
    for height in STANDARD_HEIGHTS_CM:
        if height + 1e-9 >= required_cm:
            return height
    return math.ceil(required_cm)


def _bar_selection(target_cm2: float, rib_width_cm: float, cover_cm: float) -> tuple[str, float, float]:
    candidates: list[tuple[float, int, str, float]] = []
    available_width = rib_width_cm - 2.0 * cover_cm
    for label, diameter_mm in BAR_OPTIONS:
        diameter_cm = diameter_mm / 10.0
        area = bar_area_cm2(diameter_mm)
        for number in (1, 2):
            clear = max(diameter_cm, 2.5)
            needed_width = number * diameter_cm + (number - 1) * clear
            if needed_width <= available_width + 1e-9 and number * area + 1e-9 >= target_cm2:
                candidates.append((number * area, number, label, diameter_mm))
    if not candidates:
        return "REQUIERE REDISEÑO", 0.0, 0.0
    # En una vigueta angosta se prefiere una sola barra que satisfaga el área;
    # si no existe, se selecciona la pareja de menor área suficiente.
    area, number, label, diameter = min(candidates, key=lambda item: (item[1], item[0], item[3]))
    return f"{number} {label}", diameter, area


def _rectangular_required_as(mu_tfm: float, b_cm: float, d_cm: float, fc: float, fy: float) -> tuple[float, float, float]:
    rn = mu_tfm * 100_000.0 / (PHI_FLEXURE * b_cm * d_cm**2)
    radicand = 0.85**2 - 1.70 * rn / fc
    if radicand <= 0:
        raise ValueError("La sección no admite una solución simplemente reforzada con las dimensiones indicadas.")
    omega = 0.85 - math.sqrt(radicand)
    rho = omega * fc / fy
    return rho * b_cm * d_cm, omega, rho


def _required_as(mu_tfm: float, b_cm: float, bw_cm: float, hf_cm: float, d_cm: float, fc: float, fy: float, positive: bool) -> tuple[float, float, float]:
    """Calculate required steel, including the T-section case at positive moment."""
    as_required, omega, rho = _rectangular_required_as(mu_tfm, b_cm, d_cm, fc, fy)
    a_rect = as_required * fy / (0.85 * fc * b_cm)
    if not positive or a_rect <= hf_cm:
        return as_required, omega, rho

    mn_required = mu_tfm * 100_000.0 / PHI_FLEXURE
    flange_force = 0.85 * fc * (b_cm - bw_cm) * hf_cm
    flange_moment = flange_force * (d_cm - hf_cm / 2.0)
    web_moment = max(0.0, mn_required - flange_moment)
    radicand = d_cm**2 - 2.0 * web_moment / (0.85 * fc * bw_cm)
    if radicand <= 0:
        raise ValueError("La sección T no admite una solución simplemente reforzada con las dimensiones indicadas.")
    a = d_cm - math.sqrt(radicand)
    as_required = 0.85 * fc * (bw_cm * a + (b_cm - bw_cm) * hf_cm) / fy
    rho = as_required / (b_cm * d_cm)
    omega = rho * fy / fc
    return as_required, omega, rho


def _section_capacity(as_cm2: float, b_cm: float, bw_cm: float, hf_cm: float, d_cm: float, fc: float, fy: float, positive: bool) -> tuple[float, float, str]:
    if positive:
        a_rect = as_cm2 * fy / (0.85 * fc * b_cm)
        if a_rect <= hf_cm:
            mn = as_cm2 * fy * (d_cm - a_rect / 2.0)
            return a_rect, mn / 100_000.0, "Rectangular dentro del ala"
        a = (as_cm2 * fy / (0.85 * fc) - (b_cm - bw_cm) * hf_cm) / bw_cm
        c_web = 0.85 * fc * bw_cm * a
        c_flange = 0.85 * fc * (b_cm - bw_cm) * hf_cm
        mn = c_web * (d_cm - a / 2.0) + c_flange * (d_cm - hf_cm / 2.0)
        return a, mn / 100_000.0, "Sección T"
    a = as_cm2 * fy / (0.85 * fc * bw_cm)
    mn = as_cm2 * fy * (d_cm - a / 2.0)
    return a, mn / 100_000.0, "Rectangular: ancho del nervio"


def _design_flexure(location: str, kind: str, coefficient: float, length_m: float, width_cm: float, inputs: SlabInputs, h_cm: float, d_cm: float, wu_line: float) -> FlexureResult:
    positive = kind == "Positivo"
    mu = coefficient * wu_line * length_m**2
    as_calc, omega, rho = _required_as(
        mu, width_cm, inputs.rib_width_cm, inputs.topping_cm, d_cm,
        inputs.fc_kg_cm2, inputs.fy_kg_cm2, positive,
    )

    # E.060 10.5.2, expresada en MPa y mm; se reporta aunque se adopta la ruta 10.5.3.
    fc_mpa = inputs.fc_kg_cm2 * KGCM2_TO_MPA
    fy_mpa = inputs.fy_kg_cm2 * KGCM2_TO_MPA
    as_min_mm2 = 0.22 * math.sqrt(fc_mpa) / fy_mpa * (inputs.rib_width_cm * 10.0) * (d_cm * 10.0)
    as_min = as_min_mm2 / 100.0

    # Ruta simplificada de E.060 10.5.3: proporcionar por lo menos 4/3 del acero requerido.
    as_target = (4.0 / 3.0) * as_calc
    bar_label, diameter_mm, as_provided = _bar_selection(as_target, inputs.rib_width_cm, inputs.cover_cm)
    messages: list[str] = []
    if as_provided == 0:
        return FlexureResult(location, kind, coefficient, length_m, width_cm, mu, omega, rho, as_calc, as_min, as_target, bar_label, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, "Sin solución", "REVISAR", ["El acero requerido no cabe en el nervio."])

    a_cm, mn_tfm, section_model = _section_capacity(
        as_provided, width_cm, inputs.rib_width_cm, inputs.topping_cm, d_cm,
        inputs.fc_kg_cm2, inputs.fy_kg_cm2, positive,
    )
    beta1 = 0.85 if inputs.fc_kg_cm2 * KGCM2_TO_MPA <= 28.0 else max(0.65, 0.85 - 0.05 * ((inputs.fc_kg_cm2 * KGCM2_TO_MPA - 28.0) / 7.0))
    c_cm = a_cm / beta1
    eps_t = 0.003 * (d_cm - c_cm) / c_cm if c_cm > 0 else 0.0
    phi_mn = PHI_FLEXURE * mn_tfm
    if positive and a_cm > inputs.topping_cm:
        messages.append("El bloque de compresión excede la losa superior; se aplicó el modelo de sección T.")
    checks = (
        phi_mn + 1e-9 >= mu,
        as_provided + 1e-9 >= as_target,
        eps_t + 1e-9 >= 0.004,
    )
    if not checks[0]:
        messages.append("La resistencia a flexión es insuficiente.")
    if not checks[1]:
        messages.append("No se satisface la ruta simplificada de E.060 10.5.3.")
    if not checks[2]:
        messages.append("La deformación neta de tracción es menor que 0,004.")
    status = "CUMPLE" if all(checks) else "REVISAR"
    return FlexureResult(location, kind, coefficient, length_m, width_cm, mu, omega, rho, as_calc, as_min, as_target, bar_label, diameter_mm, as_provided, a_cm, c_cm, eps_t, phi_mn, section_model, status, messages)


def _development_for_bar(label: str, diameter_mm: float, inputs: SlabInputs, h_cm: float) -> DevelopmentResult:
    fc_mpa = inputs.fc_kg_cm2 * KGCM2_TO_MPA
    fy_mpa = inputs.fy_kg_cm2 * KGCM2_TO_MPA
    concrete_below_bar_cm = h_cm - inputs.cover_cm - diameter_mm / 20.0
    psi_t = 1.3 if concrete_below_bar_cm >= 30.0 else 1.0
    psi_e = 1.5 if inputs.epoxy_coated else 1.0
    psi_s = 0.8 if diameter_mm <= 19.05 + 1e-9 else 1.0
    lambda_factor = 1.3 if inputs.lightweight_concrete else 1.0
    cb_mm = min((inputs.cover_cm + diameter_mm / 20.0) * 10.0, inputs.rib_spacing_cm * 10.0 / 2.0)
    confinement = min(cb_mm / diameter_mm, 2.5)
    ld_mm = (fy_mpa / (1.1 * math.sqrt(fc_mpa))) * (psi_t * psi_e * psi_s * lambda_factor / confinement) * diameter_mm
    ld_mm = max(ld_mm, 300.0)
    ldh_mm = 0.24 * psi_e * lambda_factor * fy_mpa / math.sqrt(fc_mpa) * diameter_mm
    ldh_mm = max(ldh_mm, min(8.0 * diameter_mm, 150.0))
    status = "CUMPLE" if inputs.available_anchor_cm * 10.0 + 1e-9 >= ld_mm else "REQUIERE GANCHO O MAYOR LONGITUD"
    return DevelopmentResult(label, diameter_mm, ld_mm / 10.0, ldh_mm / 10.0, inputs.available_anchor_cm, status)


def design_slab(inputs: SlabInputs) -> DesignResult:
    if len(inputs.spans_m) < 2:
        raise ValueError("El método aproximado requiere dos o más tramos.")
    if any(span <= 0 for span in inputs.spans_m):
        raise ValueError("Todas las luces deben ser mayores que cero.")
    required_height, required_by_span = _required_height(inputs.spans_m)
    height = inputs.manual_height_cm if inputs.manual_height_cm is not None else _select_height(required_height)
    d_cm = height - inputs.effective_depth_offset_cm
    if d_cm <= 0:
        raise ValueError("El peralte efectivo debe ser mayor que cero.")

    self_weight = inputs.slab_self_weight_kg_m2 if inputs.slab_self_weight_kg_m2 is not None else default_self_weight(height)
    dead = self_weight + inputs.finishes_kg_m2 + inputs.partitions_kg_m2
    factored = 1.4 * dead + 1.7 * inputs.live_load_kg_m2
    wu_line = factored * (inputs.rib_spacing_cm / 100.0) / 1000.0

    flexure: list[FlexureResult] = []
    last_span = len(inputs.spans_m) - 1
    for index, span in enumerate(inputs.spans_m):
        coefficient = 1.0 / 11.0 if index in (0, last_span) else 1.0 / 16.0
        flexure.append(_design_flexure(f"Tramo {index + 1}", "Positivo", coefficient, span, inputs.rib_spacing_cm, inputs, height, d_cm, wu_line))

    exterior_coeff = {"Viga de borde": 1.0 / 24.0, "Columna": 1.0 / 16.0, "No restringido": 0.0}.get(inputs.outer_support, 1.0 / 24.0)
    if exterior_coeff > 0:
        flexure.append(_design_flexure("Apoyo exterior izquierdo", "Negativo", exterior_coeff, inputs.spans_m[0], inputs.rib_width_cm, inputs, height, d_cm, wu_line))
    for support in range(1, len(inputs.spans_m)):
        if len(inputs.spans_m) == 2:
            coefficient = 1.0 / 9.0
        elif support in (1, len(inputs.spans_m) - 1):
            coefficient = 1.0 / 10.0
        else:
            coefficient = 1.0 / 11.0
        average_span = (inputs.spans_m[support - 1] + inputs.spans_m[support]) / 2.0
        flexure.append(_design_flexure(f"Apoyo interior {support}", "Negativo", coefficient, average_span, inputs.rib_width_cm, inputs, height, d_cm, wu_line))
    if exterior_coeff > 0:
        flexure.append(_design_flexure("Apoyo exterior derecho", "Negativo", exterior_coeff, inputs.spans_m[-1], inputs.rib_width_cm, inputs, height, d_cm, wu_line))

    vu_candidates = []
    for support in range(1, len(inputs.spans_m)):
        average_span = (inputs.spans_m[support - 1] + inputs.spans_m[support]) / 2.0
        multiplier = 1.15 if support in (1, len(inputs.spans_m) - 1) else 1.0
        vu_candidates.append(multiplier * 0.5 * wu_line * average_span)
    vu_max = max(vu_candidates)
    vc = 1.10 * 0.53 * math.sqrt(inputs.fc_kg_cm2) * inputs.rib_width_cm * d_cm / 1000.0
    phi_vc = PHI_SHEAR * vc
    shear_status = "CUMPLE" if phi_vc + 1e-9 >= vu_max else "REQUIERE REVISIÓN POR CORTANTE"

    temp_as = 0.0018 * 100.0 * inputs.topping_cm
    temp_area = bar_area_cm2(inputs.temperature_bar_mm)
    temp_spacing_area = 100.0 * temp_area / temp_as
    temp_spacing_limit = min(5.0 * inputs.topping_cm, 40.0)
    temp_spacing = math.floor(min(temp_spacing_area, temp_spacing_limit) / 5.0) * 5.0
    temp_spacing = max(temp_spacing, 5.0)
    temp_label = next((label for label, diameter in BAR_OPTIONS if abs(diameter - inputs.temperature_bar_mm) < 0.2), f"Ø {inputs.temperature_bar_mm:g} mm")

    unique_bars = {}
    for item in flexure:
        if item.bar_diameter_mm > 0:
            unique_bars[round(item.bar_diameter_mm, 3)] = item.bar_label.split(" ", 1)[-1]
    development = [_development_for_bar(label, diameter, inputs, height) for diameter, label in sorted(unique_bars.items())]

    clear_spacing = inputs.rib_spacing_cm - inputs.rib_width_cm
    geometry_checks = [
        ("Ancho mínimo del nervio", f"{inputs.rib_width_cm:.1f} cm ≥ 10 cm", "CUMPLE" if inputs.rib_width_cm >= 10.0 else "NO CUMPLE"),
        ("Relación altura/ancho", f"{height:.1f} cm ≤ {3.5 * inputs.rib_width_cm:.1f} cm", "CUMPLE" if height <= 3.5 * inputs.rib_width_cm else "NO CUMPLE"),
        ("Separación libre", f"{clear_spacing:.1f} cm ≤ 75 cm", "CUMPLE" if clear_spacing <= 75.0 else "NO CUMPLE"),
        ("Losa superior", f"{inputs.topping_cm:.1f} cm ≥ {max(clear_spacing / 12.0, 5.0):.1f} cm", "CUMPLE" if inputs.topping_cm >= max(clear_spacing / 12.0, 5.0) else "NO CUMPLE"),
        ("Espesor por deflexión", f"{height:.1f} cm ≥ {required_height:.2f} cm", "CUMPLE" if height + 1e-9 >= required_height else "NO CUMPLE"),
    ]
    ratios_ok = all(max(a, b) / min(a, b) <= 1.20 + 1e-9 for a, b in zip(inputs.spans_m, inputs.spans_m[1:]))
    method_checks = [
        ("Número de tramos", f"{len(inputs.spans_m)} tramos ≥ 2", "CUMPLE"),
        ("Luces adyacentes", "Diferencia ≤ 20 %" if ratios_ok else "Diferencia > 20 %", "CUMPLE" if ratios_ok else "NO CUMPLE"),
        ("Carga viva", f"{inputs.live_load_kg_m2:.1f} ≤ 3({dead:.1f}) kgf/m²", "CUMPLE" if inputs.live_load_kg_m2 <= 3.0 * dead else "NO CUMPLE"),
        ("Carga distribuida", "Uniforme en todos los tramos", "CUMPLE"),
        ("Sección", "Constante en todos los tramos", "CUMPLE"),
    ]
    warnings = []
    if not ratios_ok:
        warnings.append("El método de coeficientes de E.060 8.3.4 no es aplicable porque dos luces adyacentes difieren más de 20 %.")
    if inputs.manual_height_cm is not None and inputs.manual_height_cm < required_height:
        warnings.append("El espesor manual es menor que el requerido por la Tabla 9.1; se necesita verificar deflexiones.")
    if inputs.slab_self_weight_kg_m2 is None and height not in STANDARD_HEIGHTS_CM:
        warnings.append("El peso propio de una altura no tabulada se obtuvo por interpolación; para el diseño final ingrese el peso real del sistema empleado.")
    if inputs.outer_support == "No restringido":
        warnings.append("No se asignó momento negativo en los apoyos exteriores.")
    if any(item.straight_status != "CUMPLE" for item in development):
        warnings.append("Al menos una barra no dispone de longitud recta suficiente; revisar gancho, continuidad o geometría del apoyo.")

    return DesignResult(inputs, required_height, height, d_cm, dead, factored, wu_line, flexure, vu_max, vc, phi_vc, shear_status, temp_as, temp_spacing, temp_label, development, geometry_checks, method_checks, warnings)
