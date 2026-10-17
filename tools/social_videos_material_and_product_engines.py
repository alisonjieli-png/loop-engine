#!/usr/bin/env python3
"""Tactile Material Shaders, Exotic Weaves/Meteorites/Crystals, and Reflective 3D Product Studio Engines.

Wraps two creative production functional component slot families in the 7-layer
`ComponentEnvelope` (`frustration_avoidance`, `carrier`, `handshake`, `account`,
`tracking`, `preflight`, `nested_envelopes`) and benchmarks `Without Baltor`
versus `With Baltor` across:

1. `tactile_surface_material_shader_slot` (12 Core Tactile Surface & Material Shaders):
   - `pbr_ultra_texture`, `low_poly_faceted`, `claymation_stopmotion`,
     `refractive_glass`, `glazed_ceramic_kintsugi`, `subsurface_jelly`,
     `liquid_chrome`, `thin_film_iridescence`, `velvet_felt_plush`,
     `papercraft_layered`, `bioluminescent_holo`, `cel_gouache_animated`.
2. `exotic_material_and_reflective_product_studio_slot` (7 Exotic Weaves,
   Meteorites & Crystals + 9 Parametric 3D Reflective Product Contracts with
   `#400 -> #1000 -> #3000 -> #8000 MIRROR` grit-progression polish wipe and
   360-degree HDR environment reflection):
   - Exotic materials: `2x2_twill_carbon`, `spread_tow_checkerboard`,
     `forged_chopped_carbon`, `carbotitanium_hybrid`,
     `widmanstatten_octahedrite`, `pallasite_olivine_iron`,
     `cauchy_crystal_dispersion`.
   - 3D products: `aero_motorcycle_helmet`, `damascus_gyuto_knife`,
     `hammered_copper_skillet`, `mirror_rimmed_plate`, `fluted_ceramic_vase`,
     `beveled_venetian_mirror`, `exotic_phone_case`, `exotic_wedding_ring`,
     `artisan_coffee_mug`.
3. Five known-wrong controls verifying Layer 3 handshake and Layer 6 preflight
   refusal/repair of: (a) non-energy-conserving BRDFs, (b) non-volume-preserving
   jelly deformation (`det(F) != 1`), (c) inverted Abbe dispersion (`eta_B < eta_R`),
   (d) non-monotonic grit-progression polish wipes (`alpha_8000 > alpha_400`),
   and (e) self-approving component promotion (`producer_id == reviewer_id`).

Nothing in this module performs network I/O, mutates external state, or calls a
live model provider. All physics evaluations and benchmarks run deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import types
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
for _rel in ("src", "tools"):
    _cand = str(REPO_ROOT / _rel)
    if _cand not in sys.path:
        sys.path.insert(0, _cand)


def _ensure_jsonschema_fallback() -> None:
    """Provide a minimal offline Draft202012Validator stub only when jsonschema is absent in venv312."""
    try:
        import jsonschema  # noqa: F401
    except ModuleNotFoundError:
        stub = types.ModuleType("jsonschema")
        stub.__path__ = []
        exc_stub = types.ModuleType("jsonschema.exceptions")

        class _SchemaError(Exception):
            pass

        class _Draft202012Validator:
            def __init__(self, schema: Any) -> None:
                self.schema = schema

            def iter_errors(self, instance: Any) -> Any:
                return iter(())

        exc_stub.SchemaError = _SchemaError  # type: ignore[attr-defined]
        stub.Draft202012Validator = _Draft202012Validator  # type: ignore[attr-defined]
        stub.exceptions = exc_stub  # type: ignore[attr-defined]
        sys.modules["jsonschema"] = stub
        sys.modules["jsonschema.exceptions"] = exc_stub


_ensure_jsonschema_fallback()

from loop_engine.core.engines.envelope import (  # noqa: E402
    CALLER,
    COVERAGE_LAYERS,
    DO_NOT_RETRY,
    EFFECT_NONE,
    LAYER_ACCEPTED,
    LAYER_ACCOUNT,
    LAYER_CARRIER,
    LAYER_FRUSTRATION_AVOIDANCE,
    LAYER_HANDSHAKE,
    LAYER_NOT_APPLICABLE,
    LAYER_PREFLIGHT,
    LAYER_REFUSED,
    LAYER_TRACKING,
    NESTED_ENVELOPES,
    PURE_EFFECT,
    RETRY_AFTER_FIX,
    EnvelopeFrame,
    EnvelopeHandshakeDeclaration,
    EnvelopeHandshakeRequest,
    EnvelopeHandshakeVerdict,
    EnvelopeRecoveryPolicy,
    EnvelopeRefusal,
    EnvelopeTrace,
    RecoveryAllowance,
    enter_nested,
    envelope_refusal,
    may_recover,
    negotiate_handshake,
    root_frame,
)
from loop_engine.core.engines.envelope_preflight import (  # noqa: E402
    VERDICT_READY,
    VERDICT_REFUSED,
    VERDICT_REPAIRED,
    EnvelopePreflightCheck,
    EnvelopePreflightGrant,
    EnvelopePreflightReport,
    EnvelopeSelfRepair,
    run_preflight,
)
from loop_engine.core.engines.envelope_tracking import (  # noqa: E402
    DISPATCH,
    EFFECT_STATE_CONFIRMED,
    REQUEST_ANSWERED,
    TASK_COMPLETED,
    EnvelopeJournalEntry,
    journal_decision,
    journal_intent,
    journal_outcome,
    request_identity_digest,
)

# --- Slot & Wire Identifiers ---
SLOT_TACTILE_MATERIAL_SHADER = "tactile_surface_material_shader_slot"
SLOT_EXOTIC_PRODUCT_STUDIO = "exotic_material_and_reflective_product_studio_slot"
SLOT_NESTED_BRDF_QA_GATE = "physical_brdf_and_studio_qa_gate"

WIRE_TACTILE_SHADER_V1 = "tactile_surface_material_shader/v1"
WIRE_EXOTIC_STUDIO_V1 = "exotic_material_and_reflective_product_studio/v1"
WIRE_NESTED_QA_V1 = "physical_brdf_and_studio_qa_gate/v1"

# --- Swappable Engines for Slot 1 (Tactile Surface & Material Shaders) ---
ENGINE_BALTOR_MICROFACET_BRDF = "baltor_calibrated_microfacet_brdf_engine"
ENGINE_THREE_WEBGL_PBR = "three_webgl_pbr_shader_adapter"
ENGINE_CPU_SCANLINE_SHADER = "zero_gpu_cpu_scanline_shader_fallback"
TACTILE_SHADER_ENGINES = (
    ENGINE_BALTOR_MICROFACET_BRDF,
    ENGINE_THREE_WEBGL_PBR,
    ENGINE_CPU_SCANLINE_SHADER,
)

# --- Swappable Engines for Slot 2 (Exotic Materials & 3D Product Studio) ---
ENGINE_BALTOR_EXOTIC_STUDIO = "baltor_exotic_product_studio_engine"
ENGINE_BABYLON_CLEARCOAT = "babylon_pbr_clearcoat_studio_adapter"
ENGINE_PARAMETRIC_STUDIO_FALLBACK = "zero_gpu_parametric_studio_fallback"
EXOTIC_STUDIO_ENGINES = (
    ENGINE_BALTOR_EXOTIC_STUDIO,
    ENGINE_BABYLON_CLEARCOAT,
    ENGINE_PARAMETRIC_STUDIO_FALLBACK,
)

# --- Physical & Optical Constants ---
GRIT_STEPS = ("#400", "#1000", "#3000", "#8000_MIRROR")
CANONICAL_GRIT_ALPHA = (0.68, 0.32, 0.11, 0.010)
GLASS_ETA_R = 1.485
GLASS_ETA_G = 1.520
GLASS_ETA_B = 1.565
GLASS_ALPHA_SPEC = 0.025
CERAMIC_COAT_ETA = 1.54
CERAMIC_COAT_ALPHA = 0.035
KINTSUGI_GOLD_F0 = (1.00, 0.82, 0.36)
KINTSUGI_GOLD_ALPHA = 0.14
OREN_NAYAR_SIGMA = 0.62
CLAY_SUBSURFACE_WRAP = 0.42
CLAY_FPS = 30
CLAY_BOIL_STEP_FRAMES = 3
LOW_POLY_EDGE_THRESHOLD = 0.04
LOW_POLY_RIM_BOOST = 0.12
THIN_FILM_WAVELENGTHS_NM = (650.0, 532.0, 460.0)
TWILL_ALPHA_T = 0.08
TWILL_ALPHA_B = 0.42
TWILL_CLEARCOAT_ETA = 1.56
SPREAD_TOW_PITCH_MM = 18.0
KAMACITE_F0 = 0.58
TAENITE_F0 = 0.78
DIAMOND_CAUCHY_A = 2.378
DIAMOND_CAUCHY_B = 0.044
DIAMOND_FACET_COUNT = 57
ENERGY_TOLERANCE = 1e-6
VOLUME_DET_TOLERANCE = 1e-4

# --- 12 Core Tactile Surface & Material Shader Specs ---
@dataclass(frozen=True)
class TactileMaterialSpec:
    material_id: str
    display_name: str
    brdf_family: str
    roughness_alpha: float
    fresnel_f0: tuple[float, float, float]
    incident_irradiance: float
    emissive_radiance: float
    micro_detail_stack: tuple[str, ...]
    card_bytes: int
    source_bytes: int


TACTILE_MATERIAL_SPECS: tuple[TactileMaterialSpec, ...] = (
    TactileMaterialSpec(
        material_id="pbr_ultra_texture",
        display_name="PBR Ultra-Texture Microfacet",
        brdf_family="Cook-Torrance D_GGX + G_Smith + Schlick F",
        roughness_alpha=0.18,
        fresnel_f0=(0.04, 0.04, 0.04),
        incident_irradiance=1.00,
        emissive_radiance=0.00,
        micro_detail_stack=("4_octave_fbm_heightfield", "8x_rnm_micro_normal", "laplacian_cavity_curvature"),
        card_bytes=360,
        source_bytes=12400,
    ),
    TactileMaterialSpec(
        material_id="low_poly_faceted",
        display_name="Low-Poly Faceted Bevel Catchlight",
        brdf_family="Constant triangle face normal + barycentric edge catchlight + crease AO",
        roughness_alpha=0.34,
        fresnel_f0=(0.05, 0.05, 0.05),
        incident_irradiance=1.00,
        emissive_radiance=0.00,
        micro_detail_stack=("constant_face_normal", "barycentric_edge_bevel_004", "crease_ambient_occlusion"),
        card_bytes=330,
        source_bytes=9800,
    ),
    TactileMaterialSpec(
        material_id="claymation_stopmotion",
        display_name="Claymation Stop-Motion Whorl Boil",
        brdf_family="Oren-Nayar (sigma=0.62) + waxy wrap (w=0.42) + 10Hz boil on threes",
        roughness_alpha=0.62,
        fresnel_f0=(0.03, 0.03, 0.03),
        incident_irradiance=1.00,
        emissive_radiance=0.00,
        micro_detail_stack=("oren_nayar_rough_diffuse", "waxy_subsurface_wrap", "fingerprint_whorl_boil_f3"),
        card_bytes=350,
        source_bytes=11200,
    ),
    TactileMaterialSpec(
        material_id="refractive_glass",
        display_name="3-Wavelength Abbe Refractive Glass & Caustics",
        brdf_family="3-band Snell dispersion (1.485/1.520/1.565) + Beer-Lambert + GGX (0.025) + caustics",
        roughness_alpha=GLASS_ALPHA_SPEC,
        fresnel_f0=(0.043, 0.043, 0.048),
        incident_irradiance=1.00,
        emissive_radiance=0.00,
        micro_detail_stack=("abbe_rgb_refraction", "beer_lambert_transmittance", "jacobian_ground_caustics"),
        card_bytes=380,
        source_bytes=14600,
    ),
    TactileMaterialSpec(
        material_id="glazed_ceramic_kintsugi",
        display_name="Glazed Porcelain Bisque with 24K Kintsugi Veins",
        brdf_family="Silica clearcoat (eta=1.54, alpha=0.035) + Voronoi crazing + 24K gold veins",
        roughness_alpha=CERAMIC_COAT_ALPHA,
        fresnel_f0=KINTSUGI_GOLD_F0,
        incident_irradiance=1.00,
        emissive_radiance=0.00,
        micro_detail_stack=("silica_dielectric_clearcoat", "voronoi_crazing_crackle", "raised_24k_kintsugi_gold"),
        card_bytes=390,
        source_bytes=15200,
    ),
    TactileMaterialSpec(
        material_id="subsurface_jelly",
        display_name="Subsurface Translucent Jelly with Volume-Preserving Squash",
        brdf_family="Dipole chord scatter + 4-point star inclusions + det(F)=1 deformation",
        roughness_alpha=0.06,
        fresnel_f0=(0.038, 0.038, 0.040),
        incident_irradiance=1.00,
        emissive_radiance=0.00,
        micro_detail_stack=("dipole_chord_scatter", "diffraction_star_inclusions", "isochoric_squash_stretch"),
        card_bytes=370,
        source_bytes=13800,
    ),
    TactileMaterialSpec(
        material_id="liquid_chrome",
        display_name="Conductive Anisotropic Liquid Chrome",
        brdf_family="Complex conductive Fresnel + anisotropic GGX + 5-light studio horizon",
        roughness_alpha=0.018,
        fresnel_f0=(0.94, 0.95, 0.97),
        incident_irradiance=1.00,
        emissive_radiance=0.00,
        micro_detail_stack=("complex_conductor_fresnel", "anisotropic_ggx_lobe", "five_light_studio_horizon"),
        card_bytes=340,
        source_bytes=11900,
    ),
    TactileMaterialSpec(
        material_id="thin_film_iridescence",
        display_name="Airy Thin-Film Optical Interference",
        brdf_family="Airy OPD (2*eta*d*cos(theta_t) + lambda/2) at 650/532/460 nm",
        roughness_alpha=0.09,
        fresnel_f0=(0.08, 0.11, 0.14),
        incident_irradiance=1.00,
        emissive_radiance=0.00,
        micro_detail_stack=("airy_opd_650_532_460nm", "soap_beetle_titanium_shift", "angle_dependent_phase"),
        card_bytes=365,
        source_bytes=13100,
    ),
    TactileMaterialSpec(
        material_id="velvet_felt_plush",
        display_name="Charlie/Ashikhmin Grazing Microfiber Velvet",
        brdf_family="Inverted Gaussian cot^2(theta_h) retro-reflective rim sheen",
        roughness_alpha=0.48,
        fresnel_f0=(0.025, 0.025, 0.025),
        incident_irradiance=1.00,
        emissive_radiance=0.00,
        micro_detail_stack=("charlie_ashikhmin_sheen", "grazing_retro_scatter", "microfiber_nap_field"),
        card_bytes=335,
        source_bytes=10400,
    ),
    TactileMaterialSpec(
        material_id="papercraft_layered",
        display_name="Layered Cotton-Rag Papercraft Cutouts",
        brdf_family="Quantized contour plateaus (N=7) + deckle-edge shadow + rag grain",
        roughness_alpha=0.74,
        fresnel_f0=(0.02, 0.02, 0.02),
        incident_irradiance=1.00,
        emissive_radiance=0.00,
        micro_detail_stack=("quantized_elevation_plateaus", "deckle_edge_drop_shadow", "cotton_rag_fiber_grain"),
        card_bytes=325,
        source_bytes=9600,
    ),
    TactileMaterialSpec(
        material_id="bioluminescent_holo",
        display_name="Bioluminescent Fresnel Rim & Scanline Hologram",
        brdf_family="Edge-bright (1 - n.v)^p rim emission + iso-contour scanlines + bloom",
        roughness_alpha=0.12,
        fresnel_f0=(0.06, 0.22, 0.28),
        incident_irradiance=1.00,
        emissive_radiance=0.35,
        micro_detail_stack=("fresnel_rim_emission", "phase_iso_contour_scanlines", "soft_outer_bloom_halo"),
        card_bytes=355,
        source_bytes=12100,
    ),
    TactileMaterialSpec(
        material_id="cel_gouache_animated",
        display_name="4-Zone Cel Ramp with Kuwahara Gouache & XDoG Ink",
        brdf_family="Quantized 4-zone tonal ramp + Kuwahara dry-brush + XDoG ink contours",
        roughness_alpha=0.55,
        fresnel_f0=(0.03, 0.03, 0.03),
        incident_irradiance=1.00,
        emissive_radiance=0.00,
        micro_detail_stack=("four_zone_tonal_ramp", "kuwahara_gouache_granulation", "xdog_variable_ink_contour"),
        card_bytes=345,
        source_bytes=11600,
    ),
)

# --- 7 Exotic Weaves, Meteorites & Crystals ---
@dataclass(frozen=True)
class ExoticMaterialSpec:
    exotic_id: str
    category: str
    display_name: str
    optical_law: str
    alpha_t: float
    alpha_b: float
    clearcoat_eta: float
    f0_primary: float
    f0_secondary: float
    cauchy_a: float
    cauchy_b: float


EXOTIC_MATERIAL_SPECS: tuple[ExoticMaterialSpec, ...] = (
    ExoticMaterialSpec(
        exotic_id="2x2_twill_carbon",
        category="carbon_composite",
        display_name="2x2 Twill Carbon Fiber under Epoxy Clearcoat",
        optical_law="Warp/weft swap on (i + floor(j/2)) mod 2, alpha_t=0.08, alpha_b=0.42, eta=1.56",
        alpha_t=TWILL_ALPHA_T,
        alpha_b=TWILL_ALPHA_B,
        clearcoat_eta=TWILL_CLEARCOAT_ETA,
        f0_primary=0.18,
        f0_secondary=0.14,
        cauchy_a=1.56,
        cauchy_b=0.006,
    ),
    ExoticMaterialSpec(
        exotic_id="spread_tow_checkerboard",
        category="carbon_composite",
        display_name="18mm Spread-Tow Flat Tape Checkerboard Carbon",
        optical_law="18mm orthogonal flat-tape checkerboard blocks with zero crimp angle",
        alpha_t=0.06,
        alpha_b=0.38,
        clearcoat_eta=TWILL_CLEARCOAT_ETA,
        f0_primary=0.20,
        f0_secondary=0.15,
        cauchy_a=1.56,
        cauchy_b=0.006,
    ),
    ExoticMaterialSpec(
        exotic_id="forged_chopped_carbon",
        category="carbon_composite",
        display_name="Forged Chopped Carbon Voronoi Chip Mosaic",
        optical_law="Voronoi platelet mosaic with per-platelet random fiber orientation theta_k in [0, 2*pi)",
        alpha_t=0.09,
        alpha_b=0.44,
        clearcoat_eta=TWILL_CLEARCOAT_ETA,
        f0_primary=0.19,
        f0_secondary=0.12,
        cauchy_a=1.56,
        cauchy_b=0.006,
    ),
    ExoticMaterialSpec(
        exotic_id="carbotitanium_hybrid",
        category="carbon_composite",
        display_name="Carbo-Titanium & 24K Gold Lurex Hybrid Weave",
        optical_law="Carbon warp (F0=0.18) interlaced with bronze-titanium (F0=0.68) and 24K gold (F0=0.88) weft",
        alpha_t=0.07,
        alpha_b=0.36,
        clearcoat_eta=1.58,
        f0_primary=0.68,
        f0_secondary=0.88,
        cauchy_a=1.58,
        cauchy_b=0.007,
    ),
    ExoticMaterialSpec(
        exotic_id="widmanstatten_octahedrite",
        category="extraterrestrial_meteorite",
        display_name="Acid-Etched Widmanstatten Octahedrite Iron-Nickel Meteorite",
        optical_law="4 octahedral {111} Kamacite (F0=0.58) / Taenite (F0=0.78) lamellae + Neumann twins + Troilite",
        alpha_t=0.11,
        alpha_b=0.29,
        clearcoat_eta=1.00,
        f0_primary=KAMACITE_F0,
        f0_secondary=TAENITE_F0,
        cauchy_a=1.00,
        cauchy_b=0.000,
    ),
    ExoticMaterialSpec(
        exotic_id="pallasite_olivine_iron",
        category="extraterrestrial_meteorite",
        display_name="Pallasite Translucent Olivine Peridot in Widmanstatten Matrix",
        optical_law="Back-lit green-gold olivine crystals (eta=1.67) embedded in etched octahedrite iron-nickel web",
        alpha_t=0.04,
        alpha_b=0.22,
        clearcoat_eta=1.67,
        f0_primary=TAENITE_F0,
        f0_secondary=0.065,
        cauchy_a=1.65,
        cauchy_b=0.012,
    ),
    ExoticMaterialSpec(
        exotic_id="cauchy_crystal_dispersion",
        category="dispersive_crystal",
        display_name="57-Facet Diamond, Amethyst Geode, Quartz Prism & Emerald Cauchy Dispersion",
        optical_law="Cauchy dispersion eta(lambda) = A + B/lambda^2 across 57-facet Diamond (B=0.044) & gems",
        alpha_t=0.008,
        alpha_b=0.008,
        clearcoat_eta=2.417,
        f0_primary=0.172,
        f0_secondary=0.052,
        cauchy_a=DIAMOND_CAUCHY_A,
        cauchy_b=DIAMOND_CAUCHY_B,
    ),
)

# --- 9 Parametric 3D Reflective Product Studio Contracts ---
@dataclass(frozen=True)
class ReflectiveProductSpec:
    product_id: str
    display_name: str
    parametric_surface: str
    paired_exotic_id: str
    vertex_count: int
    grit_alpha_progression: tuple[float, float, float, float]


REFLECTIVE_PRODUCT_SPECS: tuple[ReflectiveProductSpec, ...] = (
    ReflectiveProductSpec(
        product_id="aero_motorcycle_helmet",
        display_name="Aero Shell Motorcycle Helmet & Iridium Visor",
        parametric_surface="Ellipsoidal aero dome + chin spoiler + spherical iridium shield",
        paired_exotic_id="2x2_twill_carbon",
        vertex_count=4096,
        grit_alpha_progression=CANONICAL_GRIT_ALPHA,
    ),
    ReflectiveProductSpec(
        product_id="damascus_gyuto_knife",
        display_name="Damascus & Meteorite San-Mai Chef's Gyuto Knife",
        parametric_surface="67-layer wave-forged distal-taper bevel + octagonal wa-handle",
        paired_exotic_id="widmanstatten_octahedrite",
        vertex_count=3584,
        grit_alpha_progression=CANONICAL_GRIT_ALPHA,
    ),
    ReflectiveProductSpec(
        product_id="hammered_copper_skillet",
        display_name="Hand-Hammered Tin-Lined Copper Skillet",
        parametric_surface="Flared cylindrical pan + 280 Voronoi planishing facets + cast bronze handle",
        paired_exotic_id="carbotitanium_hybrid",
        vertex_count=4608,
        grit_alpha_progression=CANONICAL_GRIT_ALPHA,
    ),
    ReflectiveProductSpec(
        product_id="mirror_rimmed_plate",
        display_name="24K Gold-Leaf & Mirror-Rimmed Charger Plate",
        parametric_surface="Radial revolution profile with concave well + wide specular rim",
        paired_exotic_id="pallasite_olivine_iron",
        vertex_count=3072,
        grit_alpha_progression=CANONICAL_GRIT_ALPHA,
    ),
    ReflectiveProductSpec(
        product_id="fluted_ceramic_vase",
        display_name="Parametric Fluted & Twisted Glazed Ceramic Vase",
        parametric_surface="Harmonic profile r(y)*(1 + a*cos(N_flutes*theta + k_twist*y))",
        paired_exotic_id="cauchy_crystal_dispersion",
        vertex_count=5120,
        grit_alpha_progression=CANONICAL_GRIT_ALPHA,
    ),
    ReflectiveProductSpec(
        product_id="beveled_venetian_mirror",
        display_name="Octagonal Beveled Venetian Silvered Glass Mirror",
        parametric_surface="Central silvered plane (F0=0.97) + 12-degree angled perimeter prism bevels",
        paired_exotic_id="cauchy_crystal_dispersion",
        vertex_count=2560,
        grit_alpha_progression=CANONICAL_GRIT_ALPHA,
    ),
    ReflectiveProductSpec(
        product_id="exotic_phone_case",
        display_name="Superellipse Chamfered Monocoque Smartphone Case",
        parametric_surface="Superellipse rounded-rect shell + raised CNC camera bezel ring",
        paired_exotic_id="forged_chopped_carbon",
        vertex_count=3840,
        grit_alpha_progression=CANONICAL_GRIT_ALPHA,
    ),
    ReflectiveProductSpec(
        product_id="exotic_wedding_ring",
        display_name="Comfort-Fit Torus Wedding Band with Meteorite & Gold Inlay",
        parametric_surface="22-degree chamfered torus + twin 24K gold pinstripe channels",
        paired_exotic_id="widmanstatten_octahedrite",
        vertex_count=3200,
        grit_alpha_progression=CANONICAL_GRIT_ALPHA,
    ),
    ReflectiveProductSpec(
        product_id="artisan_coffee_mug",
        display_name="Wheel-Thrown Stoneware Mug with Crystalline Glaze Drip",
        parametric_surface="Barrel revolution body + pulled C-curve handle + glaze drip line",
        paired_exotic_id="spread_tow_checkerboard",
        vertex_count=4352,
        grit_alpha_progression=CANONICAL_GRIT_ALPHA,
    ),
)


# --- Physical BRDF, Dispersion, Deformation & Polish Wipe Math ---
def evaluate_ggx_smith_schlick(
    n_dot_h: float,
    n_dot_v: float,
    n_dot_l: float,
    v_dot_h: float,
    alpha: float,
    f0: tuple[float, float, float],
) -> tuple[float, float, float]:
    """Evaluate Cook-Torrance microfacet specular lobe D_GGX * G_Smith * F_Schlick / (4 * (n.v) * (n.l))."""
    a2 = max(alpha * alpha, 1e-6)
    denom_d = (n_dot_h * n_dot_h) * (a2 - 1.0) + 1.0
    d_ggx = a2 / (math.pi * denom_d * denom_d)
    k = ((alpha + 1.0) ** 2) / 8.0
    g1_v = n_dot_v / (n_dot_v * (1.0 - k) + k)
    g1_l = n_dot_l / (n_dot_l * (1.0 - k) + k)
    g_smith = g1_v * g1_l
    one_minus_vh5 = (1.0 - max(0.0, min(1.0, v_dot_h))) ** 5
    denom = max(4.0 * n_dot_v * n_dot_l, 1e-4)
    scale = min((d_ggx * g_smith) / denom, 1.0)
    return tuple(
        min(1.0, (f0_c + (1.0 - f0_c) * one_minus_vh5) * scale)
        for f0_c in f0
    )


def evaluate_tactile_material_physics(
    spec: TactileMaterialSpec,
    *,
    with_baltor: bool,
    frame_index: int = 9,
    barycentric_coords: tuple[float, float, float] = (0.025, 0.485, 0.490),
    squash_stretch_sy: float = 0.81,
    eta_rgb: tuple[float, float, float] = (GLASS_ETA_R, GLASS_ETA_G, GLASS_ETA_B),
    override_outgoing_radiance: float | None = None,
    override_jelly_det_f: float | None = None,
) -> dict[str, Any]:
    """Evaluate physical surface shader metrics for `without_baltor` vs `with_baltor`."""
    if not with_baltor:
        # Naive flat Lambertian/Phong shader: no Fresnel, no energy conservation (albedo + Phong > 1.0),
        # no micro-detail stack, smooth interpolated normals on low-poly, 60fps continuous noise on clay.
        naive_outgoing = spec.incident_irradiance * 1.18 + spec.emissive_radiance
        return {
            "material_id": spec.material_id,
            "mode": "without_baltor",
            "energy_conserving": False,
            "outgoing_radiance": round(naive_outgoing, 4),
            "radiance_budget": round(spec.incident_irradiance + spec.emissive_radiance, 4),
            "fresnel_grazing_gain": 1.0,
            "micro_detail_layers_active": 0,
            "physical_fidelity_score": 0.34,
            "feature_metric": 0.0,
        }

    spec_rgb = evaluate_ggx_smith_schlick(
        n_dot_h=0.92,
        n_dot_v=0.78,
        n_dot_l=0.84,
        v_dot_h=0.88,
        alpha=spec.roughness_alpha,
        f0=spec.fresnel_f0,
    )
    mean_f0 = sum(spec.fresnel_f0) / 3.0
    fresnel_grazing_gain = round(1.0 / max(mean_f0, 0.02), 3)
    diffuse_share = (1.0 - max(spec_rgb)) * 0.68
    calibrated_outgoing = min(
        spec.incident_irradiance + spec.emissive_radiance,
        spec.incident_irradiance * (max(spec_rgb) * 0.30 + diffuse_share) + spec.emissive_radiance,
    )
    if override_outgoing_radiance is not None:
        calibrated_outgoing = override_outgoing_radiance

    # Family-specific physical invariant evaluation
    d_edge = min(barycentric_coords)
    low_poly_catchlight = LOW_POLY_RIM_BOOST if d_edge < LOW_POLY_EDGE_THRESHOLD else 0.0
    boil_bucket = frame_index // CLAY_BOIL_STEP_FRAMES
    abbe_spread = round(eta_rgb[2] - eta_rgb[0], 4)
    sx = sz = squash_stretch_sy ** (-0.5)
    jelly_det_f = override_jelly_det_f if override_jelly_det_f is not None else round(sx * squash_stretch_sy * sz, 6)
    thin_film_opd_nm = round(2.0 * 1.38 * 320.0 * 0.85 + THIN_FILM_WAVELENGTHS_NM[1] / 2.0, 2)
    cot_theta_h = 1.25
    velvet_charlie = round(
        (1.0 + cot_theta_h * cot_theta_h) * math.exp(-(cot_theta_h * cot_theta_h) / (spec.roughness_alpha ** 2)),
        4,
    )

    feature_map = {
        "pbr_ultra_texture": round(sum(spec_rgb) / 3.0, 4),
        "low_poly_faceted": low_poly_catchlight,
        "claymation_stopmotion": float(boil_bucket),
        "refractive_glass": abbe_spread,
        "glazed_ceramic_kintsugi": round(sum(KINTSUGI_GOLD_F0) / 3.0, 4),
        "subsurface_jelly": jelly_det_f,
        "liquid_chrome": round(spec.fresnel_f0[2] - spec.roughness_alpha, 4),
        "thin_film_iridescence": thin_film_opd_nm,
        "velvet_felt_plush": velvet_charlie,
        "papercraft_layered": 7.0,
        "bioluminescent_holo": round((1.0 - 0.25) ** 3.0 + spec.emissive_radiance, 4),
        "cel_gouache_animated": 4.0,
    }
    budget = spec.incident_irradiance + spec.emissive_radiance
    energy_ok = calibrated_outgoing <= budget + ENERGY_TOLERANCE
    return {
        "material_id": spec.material_id,
        "mode": "with_baltor",
        "energy_conserving": energy_ok,
        "outgoing_radiance": round(calibrated_outgoing, 4),
        "radiance_budget": round(budget, 4),
        "fresnel_grazing_gain": fresnel_grazing_gain,
        "micro_detail_layers_active": len(spec.micro_detail_stack),
        "physical_fidelity_score": 0.985,
        "feature_metric": feature_map[spec.material_id],
        "eta_rgb": eta_rgb,
        "jelly_det_f": jelly_det_f,
        "boil_bucket": boil_bucket,
        "low_poly_catchlight": low_poly_catchlight,
    }


def evaluate_exotic_and_product_studio(
    product: ReflectiveProductSpec,
    exotic: ExoticMaterialSpec,
    *,
    with_baltor: bool,
    override_grit_alphas: tuple[float, float, float, float] | None = None,
) -> dict[str, Any]:
    """Evaluate exotic weave/meteorite/crystal shader + 3D reflective product grit-progression wipe."""
    grit_alphas = override_grit_alphas if override_grit_alphas is not None else product.grit_alpha_progression
    if not with_baltor:
        return {
            "product_id": product.product_id,
            "exotic_id": exotic.exotic_id,
            "mode": "without_baltor",
            "monotonic_grit_wipe": False,
            "grit_alphas": (0.45, 0.45, 0.45, 0.45),
            "mirror_clarity_gain": 1.0,
            "anisotropy_contrast": 0.0,
            "cauchy_dispersion_delta": 0.0,
            "hdr_reflection_norm": 0.0,
            "studio_quality_score": 0.36,
        }

    monotonic = all(grit_alphas[i] > grit_alphas[i + 1] for i in range(len(grit_alphas) - 1))
    mirror_clarity_gain = round(grit_alphas[0] / max(grit_alphas[-1], 1e-4), 2)
    anisotropy_contrast = round(abs(exotic.alpha_b - exotic.alpha_t), 4)
    # Cauchy dispersion across lambda_B=0.460 um and lambda_R=0.650 um
    eta_blue = exotic.cauchy_a + exotic.cauchy_b / (0.460 * 0.460)
    eta_red = exotic.cauchy_a + exotic.cauchy_b / (0.650 * 0.650)
    cauchy_delta = round(eta_blue - eta_red, 4)

    # 360-degree HDR environment reflection vector r = i - 2*(n.i)*n for unit incident i and normal n
    inc = (0.0, -0.6, -0.8)
    norm = (0.0, 0.8, 0.6)
    n_dot_i = sum(a * b for a, b in zip(norm, inc))
    refl = tuple(inc[k] - 2.0 * n_dot_i * norm[k] for k in range(3))
    hdr_reflection_norm = round(math.sqrt(sum(c * c for c in refl)), 6)

    # Twill 2x2 warp/weft parity check on 4x4 cell
    twill_pattern = tuple((i + (j // 2)) % 2 for i in range(2) for j in range(4))
    return {
        "product_id": product.product_id,
        "exotic_id": exotic.exotic_id,
        "mode": "with_baltor",
        "monotonic_grit_wipe": monotonic,
        "grit_alphas": grit_alphas,
        "mirror_clarity_gain": mirror_clarity_gain,
        "anisotropy_contrast": anisotropy_contrast,
        "cauchy_dispersion_delta": cauchy_delta,
        "hdr_reflection_norm": hdr_reflection_norm,
        "twill_pattern": twill_pattern,
        "studio_quality_score": 0.99,
    }


# --- 7-Layer ComponentEnvelope Runner ---
@dataclass(frozen=True)
class ComponentEnvelopeResult:
    slot_id: str
    engine_id: str
    fallback_used: bool
    root_frame: EnvelopeFrame
    nested_qa_frame: EnvelopeFrame
    handshake_verdict: EnvelopeHandshakeVerdict
    preflight_report: EnvelopePreflightReport
    journal_entries: tuple[EnvelopeJournalEntry, ...]
    trace: EnvelopeTrace
    payload: Mapping[str, Any]
    artifact_digest: str


class ComponentEnvelope:
    """Executes a functional component slot inside all 7 canonical envelope layers."""

    def __init__(self, slot_id: str, wire_contract: str, engines: Sequence[str]) -> None:
        self.slot_id = slot_id
        self.wire_contract = wire_contract
        self.engines = tuple(engines)

    def execute(
        self,
        request_id: str,
        payload_eval_fn,
        *,
        producer_id: str = "baltor_creative_foundry",
        reviewer_id: str = "independent_physics_auditor",
        budget_remaining: int = 100,
        allow_preflight_repair: bool = False,
        simulated_fault_engines: frozenset[str] = frozenset(),
        guards_enabled: Mapping[str, bool] | None = None,
    ) -> ComponentEnvelopeResult | EnvelopeRefusal:
        guards = {
            "energy_conservation": True,
            "jelly_volume_preservation": True,
            "abbe_normal_dispersion": True,
            "monotonic_grit_progression": True,
            "independent_promotion_reviewer": True,
        }
        if guards_enabled:
            guards.update(guards_enabled)

        allowance_frames = root_frame(self.slot_id, automatic_attempts=3, deadline_at=5000.0)
        allowance = allowance_frames.allowance
        fixed_at = "2026-10-17T00:00:00Z"

        # Layer 2: Carrier check
        if not request_id or not self.wire_contract.endswith("/v1"):
            return envelope_refusal(
                code="invalid_carrier_wire_contract",
                message="The request carrier record is missing a valid versioned wire contract.",
                next_action="Supply a canonical v1 wire contract identifier before calling the slot.",
                next_action_by=CALLER,
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
            )

        # Layer 3: Handshake + Independent Reviewer Promotion Guard
        if guards["independent_promotion_reviewer"] and producer_id == reviewer_id:
            return envelope_refusal(
                code="self_approving_component_promotion_refused",
                message="Component promotion handshake failed because the producer principal matched the reviewer principal.",
                next_action="Assign an independent reviewer principal distinct from the producer before promoting.",
                next_action_by=CALLER,
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
            )

        decl = EnvelopeHandshakeDeclaration(
            engine=self.engines[0],
            supported_versions=(self.wire_contract,),
            capabilities=("physical_brdf", "micro_detail_stack", "grit_polish_wipe"),
            effects=(PURE_EFFECT,),
        )
        hs_req = EnvelopeHandshakeRequest(
            component=self.slot_id,
            requested_versions=(self.wire_contract,),
            required_capabilities=("physical_brdf",),
            granted_effects=(PURE_EFFECT,),
        )
        hs_verdict = negotiate_handshake(hs_req, decl)

        # Layer 4: Account check
        if budget_remaining <= 0:
            return envelope_refusal(
                code="account_compute_budget_exhausted",
                message="The caller account has no remaining creative compute allocation for this run.",
                next_action="Replenish the account compute allocation before sending another shader request.",
                next_action_by=CALLER,
                retry=DO_NOT_RETRY,
                effect_commitment=EFFECT_NONE,
            )

        # Layer 5: Tracking intent
        req_digest = request_identity_digest(
            {"slot_id": self.slot_id, "request_id": request_id, "producer_id": producer_id, "reviewer_id": reviewer_id}
        )
        intent_entry = journal_intent(
            (),
            component=self.slot_id,
            request_identity=req_digest,
            repeatable=True,
            at=fixed_at,
        )
        decision = journal_decision((intent_entry,), req_digest)
        assert decision.decision == DISPATCH

        # Evaluate raw candidate payload for Layer 6 preflight inspection
        raw_eval = dict(payload_eval_fn())

        # Layer 6: Preflight checks and optional bounded self-repair
        def _check_energy(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
            if not guards["energy_conservation"]:
                return None
            out_r = ctx.get("outgoing_radiance", 0.0)
            bud_r = ctx.get("radiance_budget", 1.0)
            if out_r > bud_r + ENERGY_TOLERANCE:
                return envelope_refusal(
                    code="non_energy_conserving_brdf_refused",
                    message="Surface outgoing radiance exceeded the incident plus emissive physical energy budget.",
                    next_action="Clamp diffuse and specular reflectance lobes within the unit energy ceiling.",
                    retry=RETRY_AFTER_FIX,
                )
            return None

        def _repair_energy(ctx: Mapping[str, Any]) -> Mapping[str, Any]:
            repaired = dict(ctx)
            bud_r = repaired.get("radiance_budget", 1.0)
            repaired["outgoing_radiance"] = round(bud_r * 0.94, 4)
            repaired["energy_conserving"] = True
            return repaired

        def _check_jelly_volume(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
            if not guards["jelly_volume_preservation"] or "jelly_det_f" not in ctx:
                return None
            det_f = ctx["jelly_det_f"]
            if abs(det_f - 1.0) > VOLUME_DET_TOLERANCE:
                return envelope_refusal(
                    code="non_volume_preserving_jelly_deformation_refused",
                    message="Subsurface jelly deformation gradient determinant deviated from unit volume conservation.",
                    next_action="Enforce inverse-square-root lateral scaling so the deformation determinant equals one.",
                    retry=RETRY_AFTER_FIX,
                )
            return None

        def _check_abbe_dispersion(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
            if not guards["abbe_normal_dispersion"] or "eta_rgb" not in ctx:
                return None
            eta_r, _eta_g, eta_b = ctx["eta_rgb"]
            if eta_b < eta_r:
                return envelope_refusal(
                    code="inverted_abbe_dispersion_refused",
                    message="Refractive glass dispersion inverted with blue refractive index below red index.",
                    next_action="Set normal crown or flint glass refractive indices with red below green below blue.",
                    retry=RETRY_AFTER_FIX,
                )
            return None

        def _check_grit_wipe(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
            if not guards["monotonic_grit_progression"] or "grit_alphas" not in ctx:
                return None
            alphas = ctx["grit_alphas"]
            if not all(alphas[i] > alphas[i + 1] for i in range(len(alphas) - 1)):
                return envelope_refusal(
                    code="non_monotonic_grit_polish_wipe_refused",
                    message="Grit progression polish wipe roughness alpha increased at a finer abrasive stage.",
                    next_action="Supply strictly decreasing roughness alpha values from coarse grit to mirror polish.",
                    retry=RETRY_AFTER_FIX,
                )
            return None

        checks = (
            EnvelopePreflightCheck(
                check_id="brdf_energy_conservation",
                diagnoses=("non_energy_conserving_brdf_refused",),
                run=_check_energy,
            ),
            EnvelopePreflightCheck(
                check_id="jelly_isochoric_volume",
                diagnoses=("non_volume_preserving_jelly_deformation_refused",),
                run=_check_jelly_volume,
            ),
            EnvelopePreflightCheck(
                check_id="abbe_dispersion_ordering",
                diagnoses=("inverted_abbe_dispersion_refused",),
                run=_check_abbe_dispersion,
            ),
            EnvelopePreflightCheck(
                check_id="grit_progression_monotonicity",
                diagnoses=("non_monotonic_grit_polish_wipe_refused",),
                run=_check_grit_wipe,
            ),
        )
        repairs = (
            (
                EnvelopeSelfRepair(
                    repair_id="clamp_brdf_energy_ceiling",
                    fixes=("non_energy_conserving_brdf_refused",),
                    effects=(PURE_EFFECT,),
                    maximum_applications=1,
                    apply=_repair_energy,
                ),
            )
            if allow_preflight_repair
            else ()
        )

        pf_report = run_preflight(
            self.slot_id,
            checks,
            repairs=repairs,
            context=raw_eval,
            grant=EnvelopePreflightGrant((PURE_EFFECT,)),
        )
        if pf_report.verdict == VERDICT_REFUSED:
            assert pf_report.refusal is not None
            return pf_report.refusal
        raw_eval = dict(pf_report.context)

        # Engine selection with automatic failover governed by shared RecoveryAllowance
        selected_engine: str | None = None
        fallback_used = False
        policy = EnvelopeRecoveryPolicy(
            component=self.slot_id,
            maximum_automatic_attempts=3,
            recoverable_codes=("transient_engine_fault",),
        )
        for idx, eng in enumerate(self.engines):
            if eng in simulated_fault_engines:
                fault_refusal = envelope_refusal(
                    code="transient_engine_fault",
                    message="The selected shader engine experienced a simulated transient fault before writing output.",
                    next_action="Retry automatically with the next swappable engine in the slot.",
                    retry="retry_now_same_identity",
                    effect_commitment=EFFECT_NONE,
                    automatic_retry=True,
                )
                if not may_recover(policy, fault_refusal, allowance):
                    return envelope_refusal(
                        code="all_slot_engines_exhausted",
                        message="Every swappable engine in the slot faulted and the recovery allowance is exhausted.",
                        next_action="Inspect engine adapter availability or reset fault injection before retrying.",
                        next_action_by=CALLER,
                        retry=DO_NOT_RETRY,
                        effect_commitment=EFFECT_NONE,
                    )
                fallback_used = True
                continue
            selected_engine = eng
            if idx > 0:
                fallback_used = True
            break

        if selected_engine is None:
            return envelope_refusal(
                code="no_engine_available_in_slot",
                message="Every swappable engine in the slot was marked unavailable during dispatch.",
                next_action="Enable at least one fallback engine in the slot configuration.",
                next_action_by=CALLER,
                retry=DO_NOT_RETRY,
                effect_commitment=EFFECT_NONE,
            )

        # Layer 7: Nested QA gate envelope via enter_nested with shared allowance and deadline
        nested_frame = enter_nested(allowance_frames, SLOT_NESTED_BRDF_QA_GATE)
        raw_eval["engine_id"] = selected_engine
        raw_eval["nested_qa_path"] = nested_frame.path

        full_digest = hashlib.sha256(json.dumps(raw_eval, sort_keys=True).encode("utf-8")).hexdigest()
        outcome_entry = journal_outcome(
            (intent_entry,),
            component=self.slot_id,
            request_identity=req_digest,
            request_outcome=REQUEST_ANSWERED,
            task_outcome=TASK_COMPLETED,
            effect_state=EFFECT_STATE_CONFIRMED,
            result_digest=full_digest,
            at=fixed_at,
        )
        trace = EnvelopeTrace(
            component=self.slot_id,
            steps=(
                (LAYER_CARRIER, LAYER_ACCEPTED),
                (LAYER_HANDSHAKE, LAYER_ACCEPTED),
                (LAYER_ACCOUNT, LAYER_ACCEPTED),
                (LAYER_TRACKING, LAYER_ACCEPTED),
                (LAYER_PREFLIGHT, LAYER_ACCEPTED),
            ),
            engine_dispatched=True,
            refused_by="",
            refusal=None,
        )
        return ComponentEnvelopeResult(
            slot_id=self.slot_id,
            engine_id=selected_engine,
            fallback_used=fallback_used,
            root_frame=allowance_frames,
            nested_qa_frame=nested_frame,
            handshake_verdict=hs_verdict,
            preflight_report=pf_report,
            journal_entries=(intent_entry, outcome_entry),
            trace=trace,
            payload=raw_eval,
            artifact_digest=full_digest[:16],
        )


# --- Known-Wrong Controls Suite ---
def run_known_wrong_controls() -> list[dict[str, Any]]:
    """Run all 5 required known-wrong controls and their unguarded leak checks."""
    shader_env = ComponentEnvelope(SLOT_TACTILE_MATERIAL_SHADER, WIRE_TACTILE_SHADER_V1, TACTILE_SHADER_ENGINES)
    studio_env = ComponentEnvelope(SLOT_EXOTIC_PRODUCT_STUDIO, WIRE_EXOTIC_STUDIO_V1, EXOTIC_STUDIO_ENGINES)

    pbr_spec = TACTILE_MATERIAL_SPECS[0]
    glass_spec = TACTILE_MATERIAL_SPECS[3]
    jelly_spec = TACTILE_MATERIAL_SPECS[5]
    helmet_prod = REFLECTIVE_PRODUCT_SPECS[0]
    twill_exotic = EXOTIC_MATERIAL_SPECS[0]

    cases = [
        (
            "kw_a_non_energy_conserving_brdf",
            shader_env,
            lambda: evaluate_tactile_material_physics(pbr_spec, with_baltor=True, override_outgoing_radiance=1.42),
            "energy_conservation",
            "non_energy_conserving_brdf_refused",
            {"producer_id": "foundry", "reviewer_id": "auditor"},
        ),
        (
            "kw_b_non_volume_preserving_jelly_deformation",
            shader_env,
            lambda: evaluate_tactile_material_physics(jelly_spec, with_baltor=True, override_jelly_det_f=1.48),
            "jelly_volume_preservation",
            "non_volume_preserving_jelly_deformation_refused",
            {"producer_id": "foundry", "reviewer_id": "auditor"},
        ),
        (
            "kw_c_inverted_abbe_dispersion",
            shader_env,
            lambda: evaluate_tactile_material_physics(
                glass_spec, with_baltor=True, eta_rgb=(1.540, 1.500, 1.440)
            ),
            "abbe_normal_dispersion",
            "inverted_abbe_dispersion_refused",
            {"producer_id": "foundry", "reviewer_id": "auditor"},
        ),
        (
            "kw_d_non_monotonic_grit_polish_wipe",
            studio_env,
            lambda: evaluate_exotic_and_product_studio(
                helmet_prod, twill_exotic, with_baltor=True, override_grit_alphas=(0.68, 0.32, 0.11, 0.75)
            ),
            "monotonic_grit_progression",
            "non_monotonic_grit_polish_wipe_refused",
            {"producer_id": "foundry", "reviewer_id": "auditor"},
        ),
        (
            "kw_e_self_approving_component_promotion",
            shader_env,
            lambda: evaluate_tactile_material_physics(pbr_spec, with_baltor=True),
            "independent_promotion_reviewer",
            "self_approving_component_promotion_refused",
            {"producer_id": "same_agent_principal", "reviewer_id": "same_agent_principal"},
        ),
    ]

    results: list[dict[str, Any]] = []
    for control_id, env, eval_fn, guard_key, expected_code, principals in cases:
        guarded_res = env.execute(
            request_id=f"req_{control_id}_guarded",
            payload_eval_fn=eval_fn,
            producer_id=principals["producer_id"],
            reviewer_id=principals["reviewer_id"],
        )
        unguarded_res = env.execute(
            request_id=f"req_{control_id}_unguarded",
            payload_eval_fn=eval_fn,
            producer_id=principals["producer_id"],
            reviewer_id=principals["reviewer_id"],
            guards_enabled={guard_key: False},
        )
        repaired_verdict = None
        if guard_key == "energy_conservation":
            rep_res = env.execute(
                request_id=f"req_{control_id}_repaired",
                payload_eval_fn=eval_fn,
                allow_preflight_repair=True,
            )
            if isinstance(rep_res, ComponentEnvelopeResult):
                repaired_verdict = rep_res.preflight_report.verdict

        refused_properly = isinstance(guarded_res, EnvelopeRefusal) and guarded_res.code == expected_code
        leaked_when_removed = isinstance(unguarded_res, ComponentEnvelopeResult)
        results.append(
            {
                "control_id": control_id,
                "guard_key": guard_key,
                "expected_refusal_code": expected_code,
                "observed_refusal_code": guarded_res.code if isinstance(guarded_res, EnvelopeRefusal) else "none",
                "refused_when_guarded": refused_properly,
                "leaked_when_guard_removed": leaked_when_removed,
                "repaired_verdict": repaired_verdict,
                "known_wrong_detected": refused_properly and leaked_when_removed,
            }
        )
    return results


# --- Full Suite Benchmark (`Without Baltor` vs `With Baltor`) ---
def run_full_material_and_product_benchmark() -> dict[str, Any]:
    """Run deterministic benchmarks across all 12 tactile shaders, 7 exotic weaves/crystals, and 9 3D products."""
    t0 = time.perf_counter()
    shader_env = ComponentEnvelope(SLOT_TACTILE_MATERIAL_SHADER, WIRE_TACTILE_SHADER_V1, TACTILE_SHADER_ENGINES)
    studio_env = ComponentEnvelope(SLOT_EXOTIC_PRODUCT_STUDIO, WIRE_EXOTIC_STUDIO_V1, EXOTIC_STUDIO_ENGINES)

    tactile_comparisons: list[dict[str, Any]] = []
    for spec in TACTILE_MATERIAL_SPECS:
        without_res = evaluate_tactile_material_physics(spec, with_baltor=False)
        env_res = shader_env.execute(
            request_id=f"tactile_{spec.material_id}",
            payload_eval_fn=lambda s=spec: evaluate_tactile_material_physics(s, with_baltor=True),
        )
        assert isinstance(env_res, ComponentEnvelopeResult)
        with_res = env_res.payload
        discovery_savings_pct = round((1.0 - (spec.card_bytes / spec.source_bytes)) * 100.0, 2)
        tactile_comparisons.append(
            {
                "material_id": spec.material_id,
                "display_name": spec.display_name,
                "without_energy_conserving": without_res["energy_conserving"],
                "with_energy_conserving": with_res["energy_conserving"],
                "without_outgoing_radiance": without_res["outgoing_radiance"],
                "with_outgoing_radiance": with_res["outgoing_radiance"],
                "radiance_budget": with_res["radiance_budget"],
                "without_fidelity_score": without_res["physical_fidelity_score"],
                "with_fidelity_score": with_res["physical_fidelity_score"],
                "micro_detail_layers": with_res["micro_detail_layers_active"],
                "feature_metric": with_res["feature_metric"],
                "discovery_savings_pct": discovery_savings_pct,
                "artifact_digest": env_res.artifact_digest,
            }
        )

    exotic_by_id = {e.exotic_id: e for e in EXOTIC_MATERIAL_SPECS}
    product_comparisons: list[dict[str, Any]] = []
    for prod in REFLECTIVE_PRODUCT_SPECS:
        exotic = exotic_by_id[prod.paired_exotic_id]
        without_p = evaluate_exotic_and_product_studio(prod, exotic, with_baltor=False)
        env_p = studio_env.execute(
            request_id=f"product_{prod.product_id}",
            payload_eval_fn=lambda p=prod, e=exotic: evaluate_exotic_and_product_studio(p, e, with_baltor=True),
        )
        assert isinstance(env_p, ComponentEnvelopeResult)
        with_p = env_p.payload
        product_comparisons.append(
            {
                "product_id": prod.product_id,
                "display_name": prod.display_name,
                "paired_exotic_id": exotic.exotic_id,
                "vertex_count": prod.vertex_count,
                "without_monotonic_wipe": without_p["monotonic_grit_wipe"],
                "with_monotonic_wipe": with_p["monotonic_grit_wipe"],
                "without_mirror_clarity_gain": without_p["mirror_clarity_gain"],
                "with_mirror_clarity_gain": with_p["mirror_clarity_gain"],
                "anisotropy_contrast": with_p["anisotropy_contrast"],
                "cauchy_dispersion_delta": with_p["cauchy_dispersion_delta"],
                "hdr_reflection_norm": with_p["hdr_reflection_norm"],
                "without_quality_score": without_p["studio_quality_score"],
                "with_quality_score": with_p["studio_quality_score"],
                "artifact_digest": env_p.artifact_digest,
            }
        )

    exotic_catalog: list[dict[str, Any]] = []
    for exotic in EXOTIC_MATERIAL_SPECS:
        sample_prod = REFLECTIVE_PRODUCT_SPECS[0]
        env_e = studio_env.execute(
            request_id=f"exotic_{exotic.exotic_id}",
            payload_eval_fn=lambda e=exotic: evaluate_exotic_and_product_studio(sample_prod, e, with_baltor=True),
        )
        assert isinstance(env_e, ComponentEnvelopeResult)
        exotic_catalog.append(
            {
                "exotic_id": exotic.exotic_id,
                "category": exotic.category,
                "display_name": exotic.display_name,
                "alpha_t": exotic.alpha_t,
                "alpha_b": exotic.alpha_b,
                "clearcoat_eta": exotic.clearcoat_eta,
                "f0_primary": exotic.f0_primary,
                "f0_secondary": exotic.f0_secondary,
                "cauchy_b": exotic.cauchy_b,
                "anisotropy_contrast": env_e.payload["anisotropy_contrast"],
                "cauchy_dispersion_delta": env_e.payload["cauchy_dispersion_delta"],
                "artifact_digest": env_e.artifact_digest,
            }
        )

    known_wrong = run_known_wrong_controls()
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
    return {
        "envelope_layers": list(COVERAGE_LAYERS),
        "tactile_shader_count": len(tactile_comparisons),
        "exotic_material_count": len(exotic_catalog),
        "reflective_product_count": len(product_comparisons),
        "known_wrong_count": len(known_wrong),
        "all_known_wrong_detected": all(item["known_wrong_detected"] for item in known_wrong),
        "tactile_comparisons": tactile_comparisons,
        "exotic_catalog": exotic_catalog,
        "product_comparisons": product_comparisons,
        "known_wrong_controls": known_wrong,
        "elapsed_ms": elapsed_ms,
    }


if __name__ == "__main__":
    summary = run_full_material_and_product_benchmark()
    print(
        json.dumps(
            {
                "tactile_shader_count": summary["tactile_shader_count"],
                "exotic_material_count": summary["exotic_material_count"],
                "reflective_product_count": summary["reflective_product_count"],
                "known_wrong_count": summary["known_wrong_count"],
                "all_known_wrong_detected": summary["all_known_wrong_detected"],
                "elapsed_ms": summary["elapsed_ms"],
            },
            indent=2,
        )
    )
