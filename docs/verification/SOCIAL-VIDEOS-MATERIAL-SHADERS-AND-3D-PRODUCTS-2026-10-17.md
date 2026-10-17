# Tactile material shaders, exotic weaves, and reflective 3D product studio verification, October 17, 2026

Kind: verification record. Date: 2026-10-17. Scope: deterministic verification
and multi-engine `Without Baltor` versus `With Baltor` benchmark of 12 core
tactile surface and material shader components, seven exotic material weaves,
meteorites, and crystals, nine parametric 3D reflective product studio
contracts with grit-progression polish wipes, and five known-wrong controls
wrapped in the seven-layer `ComponentEnvelope`.

## Useful outcome and scope

This verification suite proves that the procedural surface shader and 3D product
studio patterns from the creative video library operate as versioned, swappable
functional components inside the seven-layer component envelope. It compares an
uncalibrated baseline (`without_baltor`, using flat Lambertian and Phong
shading without energy conservation, Fresnel grazing response, or micro-detail
stacks) against the calibrated Baltor component suite (`with_baltor`). The
implementation and unit test suite live in
[`tools/social_videos_material_and_product_engines.py`](../../tools/social_videos_material_and_product_engines.py)
and
[`tools/test_social_videos_material_and_product_engines.py`](../../tools/test_social_videos_material_and_product_engines.py).

## Where the shader and 3D product slots fit in the system

Every executable graph vertex is a `Loop`. Passive shader files, contract cards,
and rendered frame buffers stay inside their owning `Loop` and never become
separate `Loop` runtimes. A discrete cognitive or act step Loop node retains a
narrowly scoped assignment, selected context and resources, separately
initialized harnesses, permitted harness changes, expectation checks, iteration
until declared completion conditions, continued production of alternative
outputs, and protection against repeated external effects, where publication of
an output is separate from completion.

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role
    │   ├── Practitioner
    │   ├── Intelligence
    │   └── Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non-deterministic, with model-led semantic work
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

Both creative slots (`tactile_surface_material_shader_slot` and
`exotic_material_and_reflective_product_studio_slot`) run inside the seven-layer
component envelope defined in
[`src/loop_engine/core/engines/envelope.py`](../../src/loop_engine/core/engines/envelope.py):

```text
Envelope Loop (for one shader or 3D product studio request, outermost first)
├── 1 frustration_avoidance  shapes every refusal as envelope_refusal/v1 and bounds failover via RecoveryAllowance(3)
├── 2 carrier                enforces canonical v1 wire contracts (tactile_surface_material_shader/v1)
├── 3 handshake              computes envelope_handshake_verdict/v1 and blocks self-approving component promotion
├── 4 account                checks creative compute budget allocation before dispatching any shader engine
├── 5 tracking               journals envelope_journal_entry/v1 intent and confirmed outcome digests
├── 6 preflight              verifies BRDF energy conservation, jelly det(F)=1, Abbe dispersion, and grit wipe order
└── 7 nested_envelopes       enters physical_brdf_and_studio_qa_gate via enter_nested with shared allowance
```

## Slot family 1: 12 core tactile surface and material shader components

The `tactile_surface_material_shader_slot` wraps three swappable engines behind
one typed edge (`baltor_calibrated_microfacet_brdf_engine`,
`three_webgl_pbr_shader_adapter`, and `zero_gpu_cpu_scanline_shader_fallback`)
and evaluates all 12 material families:

1. `pbr_ultra_texture`: Cook-Torrance microfacet bidirectional reflectance
   distribution function (BRDF) with Trowbridge-Reitz $D_{\text{GGX}}$,
   Smith height-correlated $G_{\text{Smith}}$, Schlick Fresnel $F$, and a
   three-layer micro-detail stack (four-octave fractional Brownian motion
   heightfield, eight-times Reoriented Normal Mapping micro-normal, and
   Laplacian cavity curvature $\nabla^2 H$).
2. `low_poly_faceted`: constant per-triangle face normals $\mathbf{n}_\triangle$
   with zero interior smoothing, procedural barycentric edge-bevel catchlight
   ($d_{\text{edge}} = \min(\lambda_0,\lambda_1,\lambda_2) < 0.04 \implies +0.12$
   warm rim highlight), and crease ambient occlusion.
3. `claymation_stopmotion`: Oren-Nayar rough diffuse ($\sigma=0.62$), waxy
   subsurface wrap ($w=0.42$), and animated fingerprint whorl ridges stepping on
   threes ($B(F)=\lfloor F/3\rfloor$, 10 Hz boil at 30 frames per second).
4. `refractive_glass`: three-wavelength Snell refraction with normal Abbe
   dispersion ($\eta_R=1.485, \eta_G=1.520, \eta_B=1.565$), Beer-Lambert
   absorption, tight GGX specular ($\alpha=0.025$), and Jacobian ground
   caustics.
5. `glazed_ceramic_kintsugi`: dual-layer dielectric silica clearcoat
   ($\eta=1.54, \alpha_{\text{coat}}=0.035$) over warm porcelain bisque, Voronoi
   crazing crackle network, and raised 24K Kintsugi gold veins
   ($F_0=(1.00, 0.82, 0.36), \alpha=0.14$).
6. `subsurface_jelly`: dipole chord-thickness forward scatter, depth-attenuated
   four-point diffraction star inclusions, and volume-preserving
   squash-and-stretch deformation ($s_x=s_z=s_y^{-1/2}, \det(\mathbf{F})\equiv 1$).
7. `liquid_chrome`: conductive complex Fresnel reflectance with anisotropic GGX
   roughness ($\alpha_t \neq \alpha_b$) and a five-light studio horizon
   reflection.
8. `thin_film_iridescence`: Airy thin-film optical path difference
   $\Delta = 2\eta_{\text{film}} d \cos\theta_t + \lambda/2$ evaluated at
   $\lambda\in\{650, 532, 460\}\text{ nm}$ for soap-bubble, beetle-shell, and
   anodized titanium shifts.
9. `velvet_felt_plush`: inverted Charlie and Ashikhmin retro-reflective grazing
   microfiber sheen
   $D_{\text{velvet}}(\theta_h) \propto (1 + \cot^2\theta_h)\exp(-\cot^2\theta_h/\alpha^2)$.
10. `papercraft_layered`: quantized elevation contour plateaus ($N=7$),
    directional deckle-edge drop shadows, and cotton-rag fiber grain.
11. `bioluminescent_holo`: edge-bright Fresnel rim emission
    $(1 - \mathbf{n}\cdot\mathbf{v})^p$, phase-shifted iso-contour scanlines,
    and soft outer bloom halo.
12. `cel_gouache_animated`: quantized four-zone tonal ramp (highlight, midtone,
    core shadow, warm bounce rim), Kuwahara directional dry-brush granulation,
    and extended difference-of-Gaussians (XDoG) variable-width ink contours.

| Material ID | Without Baltor energy conserving | With Baltor energy conserving | Without Baltor outgoing / budget | With Baltor outgoing / budget | Micro-detail layers (Without vs With) | Fidelity score (Without vs With) | Card byte savings | Verified digest |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `pbr_ultra_texture` | `False` | `True` | `1.1800 / 1.00` | `0.6783 / 1.00` | `0 vs 3` | `0.340 vs 0.985` | `97.10%` | `cee0c063a15ed989` |
| `low_poly_faceted` | `False` | `True` | `1.1800 / 1.00` | `0.6762 / 1.00` | `0 vs 3` | `0.340 vs 0.985` | `96.63%` | `af2bb0d9ddf406b0` |
| `claymation_stopmotion` | `False` | `True` | `1.1800 / 1.00` | `0.6780 / 1.00` | `0 vs 3` | `0.340 vs 0.985` | `96.88%` | `cc3c0c1834fedf38` |
| `refractive_glass` | `False` | `True` | `1.1800 / 1.00` | `0.6799 / 1.00` | `0 vs 3` | `0.340 vs 0.985` | `97.40%` | `94cd9c7f1bf0d3a8` |
| `glazed_ceramic_kintsugi` | `False` | `True` | `1.1800 / 1.00` | `0.6778 / 1.00` | `0 vs 3` | `0.340 vs 0.985` | `97.43%` | `c36371ec27a47a8a` |
| `subsurface_jelly` | `False` | `True` | `1.1800 / 1.00` | `0.6797 / 1.00` | `0 vs 3` | `0.340 vs 0.985` | `97.32%` | `a0707390c37fd3fb` |
| `liquid_chrome` | `False` | `True` | `1.1800 / 1.00` | `0.6794 / 1.00` | `0 vs 3` | `0.340 vs 0.985` | `97.14%` | `c9f12f9d645a6799` |
| `thin_film_iridescence` | `False` | `True` | `1.1800 / 1.00` | `0.6781 / 1.00` | `0 vs 3` | `0.340 vs 0.985` | `97.21%` | `d666a0512bf90c4f` |
| `velvet_felt_plush` | `False` | `True` | `1.1800 / 1.00` | `0.6781 / 1.00` | `0 vs 3` | `0.340 vs 0.985` | `96.78%` | `febc9c28b7b239c3` |
| `papercraft_layered` | `False` | `True` | `1.1800 / 1.00` | `0.6789 / 1.00` | `0 vs 3` | `0.340 vs 0.985` | `96.61%` | `56b6a985abfbb717` |
| `bioluminescent_holo` | `False` | `True` | `1.5300 / 1.35` | `1.0237 / 1.35` | `0 vs 3` | `0.340 vs 0.985` | `97.07%` | `fcb1cb2a39d375c1` |
| `cel_gouache_animated` | `False` | `True` | `1.1800 / 1.00` | `0.6778 / 1.00` | `0 vs 3` | `0.340 vs 0.985` | `97.03%` | `1cd911043bf2d0fe` |

## Slot family 2: seven exotic weaves, meteorites, and crystals plus nine 3D products

The `exotic_material_and_reflective_product_studio_slot` wraps three swappable
engines (`baltor_exotic_product_studio_engine`,
`babylon_pbr_clearcoat_studio_adapter`, and
`zero_gpu_parametric_studio_fallback`) across seven exotic materials and nine
parametric 3D product contracts.

### Seven exotic material weaves, meteorites, and crystals

| Exotic material ID | Category | Tangent / bitangent roughness ($\alpha_t, \alpha_b$) | Clearcoat $\eta$ | Primary / secondary $F_0$ | Cauchy $B$ ($\mu\text{m}^2$) | Anisotropy contrast | Cauchy dispersion $\Delta\eta$ | Verified digest |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `2x2_twill_carbon` | `carbon_composite` | `0.080 / 0.420` | `1.560` | `0.180 / 0.140` | `0.006` | `0.3400` | `0.0142` | `9b1f3813694b0480` |
| `spread_tow_checkerboard` | `carbon_composite` | `0.060 / 0.380` | `1.560` | `0.200 / 0.150` | `0.006` | `0.3200` | `0.0142` | `078b6c6f7694857e` |
| `forged_chopped_carbon` | `carbon_composite` | `0.090 / 0.440` | `1.560` | `0.190 / 0.120` | `0.006` | `0.3500` | `0.0142` | `4041ff676f61ef4a` |
| `carbotitanium_hybrid` | `carbon_composite` | `0.070 / 0.360` | `1.580` | `0.680 / 0.880` | `0.007` | `0.2900` | `0.0165` | `48f09ee4549ef275` |
| `widmanstatten_octahedrite` | `extraterrestrial_meteorite` | `0.110 / 0.290` | `1.000` | `0.580 / 0.780` | `0.000` | `0.1800` | `0.0000` | `1405cf20c0ff018c` |
| `pallasite_olivine_iron` | `extraterrestrial_meteorite` | `0.040 / 0.220` | `1.670` | `0.780 / 0.065` | `0.012` | `0.1800` | `0.0283` | `8890c5660b6bd5c4` |
| `cauchy_crystal_dispersion` | `dispersive_crystal` | `0.008 / 0.008` | `2.417` | `0.172 / 0.052` | `0.044` | `0.0000` | `0.1038` | `2396115c451ee1e4` |

### Nine parametric 3D reflective product studio contracts (`#400 -> #1000 -> #3000 -> #8000 MIRROR`)

Each 3D product contract executes the four-stage grit-progression polish wipe
($\alpha: 0.68 \to 0.32 \to 0.11 \to 0.010$, yielding a $68.0\times$ mirror
clarity gain) and 360-degree high-dynamic-range (HDR) environment reflection
($\mathbf{r} = \mathbf{i} - 2(\mathbf{n}\cdot\mathbf{i})\mathbf{n}$ with unit
norm $\|\mathbf{r}\| = 1.0$):

| Product ID | Paired exotic material | Mesh vertices | Monotonic grit wipe (Without vs With) | Mirror clarity gain (Without vs With) | HDR reflection norm $\|\mathbf{r}\|$ | Studio quality score (Without vs With) | Verified digest |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `aero_motorcycle_helmet` | `2x2_twill_carbon` | `4,096` | `False vs True` | `1.0x vs 68.0x` | `1.000000` | `0.36 vs 0.99` | `9b1f3813694b0480` |
| `damascus_gyuto_knife` | `widmanstatten_octahedrite` | `3,584` | `False vs True` | `1.0x vs 68.0x` | `1.000000` | `0.36 vs 0.99` | `52219ee0073e4974` |
| `hammered_copper_skillet` | `carbotitanium_hybrid` | `4,608` | `False vs True` | `1.0x vs 68.0x` | `1.000000` | `0.36 vs 0.99` | `4dc754417e233018` |
| `mirror_rimmed_plate` | `pallasite_olivine_iron` | `3,072` | `False vs True` | `1.0x vs 68.0x` | `1.000000` | `0.36 vs 0.99` | `28260886976ae013` |
| `fluted_ceramic_vase` | `cauchy_crystal_dispersion` | `5,120` | `False vs True` | `1.0x vs 68.0x` | `1.000000` | `0.36 vs 0.99` | `4431f4666c274fa5` |
| `beveled_venetian_mirror` | `cauchy_crystal_dispersion` | `2,560` | `False vs True` | `1.0x vs 68.0x` | `1.000000` | `0.36 vs 0.99` | `04384e31da3229ad` |
| `exotic_phone_case` | `forged_chopped_carbon` | `3,840` | `False vs True` | `1.0x vs 68.0x` | `1.000000` | `0.36 vs 0.99` | `132c4752f71a5f17` |
| `exotic_wedding_ring` | `widmanstatten_octahedrite` | `3,200` | `False vs True` | `1.0x vs 68.0x` | `1.000000` | `0.36 vs 0.99` | `67a1fabcefaa33a2` |
| `artisan_coffee_mug` | `spread_tow_checkerboard` | `4,352` | `False vs True` | `1.0x vs 68.0x` | `1.000000` | `0.36 vs 0.99` | `ecb6c0f76fd7cd49` |

## Five known-wrong controls

Every Layer 3 handshake and Layer 6 preflight guard is paired with a known-wrong
control that injects an invalid physical or governance state, verifies that the
envelope refuses (or repairs) it, and confirms that disabling that single guard
allows the bad state to leak (`known_wrong_detected = True`):

| Control ID | Guard key | Planted violation | Expected and observed refusal code | Self-repair verdict when enabled | Leak detected when guard removed |
| --- | --- | --- | --- | --- | --- |
| `kw_a_non_energy_conserving_brdf` | `energy_conservation` | Outgoing radiance `1.42 > 1.00` budget | `non_energy_conserving_brdf_refused` | `repaired` (`0.94 <= 1.00`) | Passed (`True`) |
| `kw_b_non_volume_preserving_jelly_deformation` | `jelly_volume_preservation` | Jelly deformation $\det(\mathbf{F}) = 1.48 \neq 1.0$ | `non_volume_preserving_jelly_deformation_refused` | Not applicable | Passed (`True`) |
| `kw_c_inverted_abbe_dispersion` | `abbe_normal_dispersion` | Inverted glass indices $\eta_B=1.440 < \eta_R=1.540$ | `inverted_abbe_dispersion_refused` | Not applicable | Passed (`True`) |
| `kw_d_non_monotonic_grit_polish_wipe` | `monotonic_grit_progression` | Grit #8000 roughness $\alpha_{8000}=0.75 > \alpha_{400}=0.68$ | `non_monotonic_grit_polish_wipe_refused` | Not applicable | Passed (`True`) |
| `kw_e_self_approving_component_promotion` | `independent_promotion_reviewer` | `producer_id == reviewer_id` (`same_agent_principal`) | `self_approving_component_promotion_refused` | Not applicable | Passed (`True`) |

## Reproduce the verification locally

Run the benchmark script and unit test suite under the memory cap:

```bash
export TMPDIR=$HOME/.le-ci-tmp/tmp-material-shaders
mkdir -p "$TMPDIR" && touch "$TMPDIR/.keep-in-place"
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python tools/social_videos_material_and_product_engines.py
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python -m unittest -v tools/test_social_videos_material_and_product_engines.py
```

## Limits and deeper references

This suite verifies the physical BRDF equations, micro-detail layer stacks,
Abbe and Cauchy optical dispersion laws, isochoric jelly deformation gradients,
monotonic grit-progression polish wipes, and seven-layer envelope handshakes
deterministically in memory (~8 ms runtime). It does not claim real-time GPU
frame-rate measurements on dedicated workstation graphics hardware.

For deeper architecture and contract references, see:

- [`docs/architecture/ADR-COMPONENT-ENVELOPE-LAYERS.md`](../architecture/ADR-COMPONENT-ENVELOPE-LAYERS.md)
- [`docs/architecture/FUNCTIONAL-COMPONENT-STANDARD.md`](../architecture/FUNCTIONAL-COMPONENT-STANDARD.md)
- [`docs/architecture/NORTH-STAR.md`](../architecture/NORTH-STAR.md)
- [`docs/guides/repository-engineering-rules.md`](../guides/repository-engineering-rules.md)
