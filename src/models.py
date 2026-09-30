from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class SlabInputs:
    spans_m: tuple[float, ...] = (3.0, 3.0, 3.0)
    fc_kg_cm2: float = 210.0
    fy_kg_cm2: float = 4200.0
    es_kg_cm2: float = 2_000_000.0
    rib_width_cm: float = 10.0
    rib_spacing_cm: float = 40.0
    topping_cm: float = 5.0
    cover_cm: float = 2.0
    effective_depth_offset_cm: float = 3.0
    manual_height_cm: Optional[float] = None
    slab_self_weight_kg_m2: Optional[float] = None
    finishes_kg_m2: float = 100.0
    partitions_kg_m2: float = 150.0
    live_load_kg_m2: float = 200.0
    outer_support: str = "Viga de borde"
    available_anchor_cm: float = 45.0
    temperature_bar_mm: float = 6.35
    epoxy_coated: bool = False
    lightweight_concrete: bool = False


@dataclass
class FlexureResult:
    location: str
    kind: str
    coefficient: float
    length_m: float
    width_cm: float
    mu_tfm: float
    omega: float
    rho: float
    as_calc_cm2: float
    as_min_cm2: float
    as_target_cm2: float
    bar_label: str
    bar_diameter_mm: float
    as_provided_cm2: float
    a_cm: float
    neutral_axis_cm: float
    tensile_strain: float
    phi_mn_tfm: float
    section_model: str
    status: str
    messages: list[str] = field(default_factory=list)


@dataclass
class DevelopmentResult:
    bar_label: str
    diameter_mm: float
    ld_cm: float
    ldh_cm: float
    available_cm: float
    straight_status: str


@dataclass
class DesignResult:
    inputs: SlabInputs
    required_height_cm: float
    selected_height_cm: float
    effective_depth_cm: float
    dead_load_kg_m2: float
    factored_load_kg_m2: float
    factored_line_load_t_m: float
    flexure: list[FlexureResult]
    vu_max_tf: float
    vc_tf: float
    phi_vc_tf: float
    shear_status: str
    temperature_as_cm2_m: float
    temperature_spacing_cm: float
    temperature_bar_label: str
    development: list[DevelopmentResult]
    geometry_checks: list[tuple[str, str, str]]
    method_checks: list[tuple[str, str, str]]
    warnings: list[str]

    @property
    def overall_status(self) -> str:
        flexure_ok = all(item.status == "CUMPLE" for item in self.flexure)
        geometry_ok = all(item[2] == "CUMPLE" for item in self.geometry_checks)
        method_ok = all(item[2] == "CUMPLE" for item in self.method_checks)
        return "CUMPLE" if flexure_ok and geometry_ok and method_ok and self.shear_status == "CUMPLE" else "REVISAR"

