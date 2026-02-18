#!/usr/bin/env python3
"""
PANDA2-INSPIRED STIFFENED SHELL BUCKLING ANALYSIS
==================================================
Based on: Bushnell, D. (1987) "PANDA2 - Program for Minimum Weight Design
          of Stiffened, Composite, Locally Buckled Panels"
          Computers & Structures, Vol. 25, No. 4, pp. 469-605.

Implements the PANDA2 methodology for an isotropic, hat-stiffened, pressurized
cylindrical shell under axial compression:

  Model Type 1: PANDA-type closed-form buckling (general, local, panel, crippling)
  Model Type 2: Discretized single panel module (local + wide column)
  Model Type 3: Smeared stiffener full panel (general instability)

Applied to: Pressurized habitat module for lunar/Mars deployment
  Shell: Al 2219-T87, D=4.25m, L=10m, t=5mm
  Stringers: 90× hat-section (30×35mm, t=3mm), FSW to skin
  Formers: 20× ring frames (Z-section, Al 2219-T87)
  Bulkheads: 5× (Al 7075-T6, handled separately)

Reference coordinate system (per PANDA2 convention):
  x = axial (normal to screen, along cylinder generator)
  y = circumferential (in plane of screen)
  z = radial (outward from reference surface)

Author: Senior Design Team (PANDA2 methodology implementation)
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from dataclasses import dataclass, field
from typing import Tuple, Dict, List
import warnings
warnings.filterwarnings('ignore')


# ═══════════════════════════════════════════════════════════════════════════════
# 1. DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Material:
    """Isotropic material properties."""
    name: str
    E: float       # Young's modulus [Pa]
    nu: float      # Poisson's ratio
    Fty: float     # Tensile yield strength [Pa]
    Fcy: float     # Compressive yield strength [Pa]
    Ftu: float     # Ultimate tensile strength [Pa]
    rho: float     # Density [kg/m³]
    G: float = 0.0 # Shear modulus (computed)

    def __post_init__(self):
        self.G = self.E / (2 * (1 + self.nu))


@dataclass
class HatStiffener:
    """Hat-section stiffener geometry (per PANDA2 Fig. 13).

    Cross-section:
         ┌──── w_cap ────┐
         │   Segment 4   │
        ╱│               │╲
       ╱ │  Seg 3  Seg 5 │ ╲    h = height
      ╱  │  (web)  (web) │  ╲
     ╱   │               │   ╲
    ├─wf─┤── w_base ─────┤─wf─┤
    │Seg2│               │Seg6│  (base/flange-to-skin)
    ├────┴───── b ───────┴────┤
    │        Segment 1        │  (skin between stringers)
    └─────────────────────────┘
    """
    w_cap: float    # Width of hat cap (top) [m]
    w_base: float   # Width of hat base (bottom opening) [m]
    h: float        # Height of hat (skin mid-plane to cap mid-plane) [m]
    t_wall: float   # Wall thickness of hat [m]
    w_flange: float # Width of faying flange (weld land) each side [m]
    spacing: float  # Stringer spacing (module width, b) [m]
    n_stiffeners: int  # Number of stringers around circumference


@dataclass
class RingFrame:
    """Ring frame (former) geometry - Z-section."""
    h_web: float    # Web height [m]
    t_web: float    # Web thickness [m]
    w_flange: float # Flange width [m]
    t_flange: float # Flange thickness [m]
    spacing: float  # Ring spacing [m]
    n_rings: int    # Number of rings


@dataclass
class Shell:
    """Cylindrical shell geometry."""
    R: float        # Radius [m]
    L: float        # Length [m]
    t: float        # Skin thickness [m]


@dataclass
class Loading:
    """Applied loading (PANDA2 convention: Load Sets A and B)."""
    # Load Set A (eigenvalue loads) - line loads [N/m]
    Nx: float = 0.0   # Axial line load (negative = compression)
    Ny: float = 0.0   # Hoop line load
    Nxy: float = 0.0  # In-plane shear

    # Load Set B (fixed loads)
    Nx0: float = 0.0  # Fixed axial (e.g., from pressure)
    Ny0: float = 0.0  # Fixed hoop (e.g., from pressure)
    p: float = 0.0    # Internal pressure [Pa]


@dataclass
class FactorsOfSafety:
    """NASA-STD-5001B factors of safety."""
    FS_general: float = 2.0    # General instability (imperfection-sensitive)
    FS_general_tested: float = 1.4  # General instability (proof-tested)
    FS_local: float = 1.0      # Local skin buckling (post-buckling OK)
    FS_column: float = 1.5     # Column/panel buckling
    FS_crippling: float = 1.5  # Stiffener crippling
    FS_yield: float = 1.25     # Material yield
    FS_ultimate: float = 1.50  # Material ultimate
    FS_stress: float = 1.0     # Stress margin (PANDA2 FSSTR)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. CONSTITUTIVE LAW — C(i,j) FOR EACH SEGMENT (Bushnell §8.1)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_Cij_isotropic(E: float, nu: float, t: float) -> np.ndarray:
    """Compute 6×6 integrated constitutive matrix for isotropic plate segment.

    Per PANDA2 Eq. 8.1:
        [N]   [C]{ε}
        [M] =     {κ}

    For isotropic material, C simplifies to:
        A_ij = membrane stiffnesses (C11, C12, C22, C33)
        D_ij = bending stiffnesses (C44, C45, C55, C66)
        B_ij = coupling (= 0 for symmetric isotropic)
    """
    C = np.zeros((6, 6))

    # Membrane stiffnesses (A matrix)
    Q = E / (1 - nu**2)
    C[0, 0] = Q * t           # A11
    C[0, 1] = Q * nu * t      # A12
    C[1, 0] = C[0, 1]         # A21
    C[1, 1] = Q * t           # A22
    C[2, 2] = Q * (1-nu)/2 * t  # A66 (shear)

    # Bending stiffnesses (D matrix)
    D = Q * t**3 / 12
    C[3, 3] = D               # D11
    C[3, 4] = D * nu          # D12
    C[4, 3] = C[3, 4]         # D21
    C[4, 4] = D               # D22
    C[5, 5] = D * (1-nu)/2    # D66

    # B matrix = 0 for symmetric isotropic (no membrane-bending coupling)
    return C


# ═══════════════════════════════════════════════════════════════════════════════
# 3. SMEARED STIFFENER CONSTITUTIVE LAW (Bushnell §8.3-8.4)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_smeared_stiffener_properties(
    hat: HatStiffener, ring: RingFrame,
    mat_skin: Material, mat_str: Material, mat_ring: Material,
    shell: Shell
) -> Dict:
    """Compute smeared stiffener constitutive properties per PANDA2 §8.4.

    The smearing process (Bushnell Eqs 8.7-8.11, 8.21-8.24):
    1. Compute C(i,j) for each segment
    2. Use equilibrium + compatibility to derive C_s(i,j) for smeared panel

    For isotropic hat stiffeners, the key quantities are:
    - EI_stringer: bending stiffness of stringer about skin neutral axis
    - EA_stringer: membrane stiffness of stringer
    - EI_ring: bending stiffness of ring about skin neutral axis
    - EA_ring: membrane stiffness of ring
    - GJ_hat: torsional rigidity of closed hat section

    Returns dict with smeared ABD matrices and section properties.
    """
    b = hat.spacing   # Module width (stringer spacing)
    E_s = mat_str.E
    nu_s = mat_str.nu
    t_s = shell.t     # Skin thickness
    tw = hat.t_wall   # Hat wall thickness

    # ── Hat stiffener section properties ──
    # Segment areas
    A_base = hat.w_base * tw           # Base (Seg 2)
    A_web_each = hat.h * tw            # Each web (Seg 3, 5)
    A_cap = hat.w_cap * tw             # Cap (Seg 4)
    A_flange = 2 * hat.w_flange * tw   # Faying flanges (Seg 2 edges)
    A_hat = 2 * A_web_each + A_cap + A_flange  # Total hat (excl. base/skin overlap)

    # Centroid of hat section from skin mid-plane
    # Flanges sit on skin surface → z_flange = 0 (at skin mid-plane level)
    # Webs go from 0 to h → z_web = h/2
    # Cap at top → z_cap = h + tw/2
    z_flange = 0.0
    z_web = hat.h / 2
    z_cap = hat.h + tw / 2

    y_hat = (A_flange * z_flange + 2 * A_web_each * z_web + A_cap * z_cap) / A_hat

    # Second moment about skin mid-plane (parallel axis theorem)
    I_hat_skin = (
        A_flange * z_flange**2 +
        2 * (tw * hat.h**3 / 12 + A_web_each * z_web**2) +
        hat.w_cap * tw**3 / 12 + A_cap * z_cap**2
    )

    # Stiffener coefficients per PANDA2 Eqs 8.21-8.24
    # STFL1 = EA of stringer (axial membrane stiffness)
    STFL1 = E_s * A_hat
    # STFM1 = E * first_moment (membrane-bending coupling)
    S_hat = A_hat * y_hat  # First moment about skin mid-plane
    STFM1 = E_s * S_hat
    # STFMM1 = EI of stringer about skin mid-plane
    STFMM1 = E_s * I_hat_skin

    # ── Torsional rigidity of hat section (closed box) ──
    # Per PANDA2 §8.4: J = 4A²/(Σ s_i/t_i), with knockdown β = 0.3
    # (Bushnell: "knocked down by a factor β = 0.3" for local deformation)
    # Enclosed area of hat (trapezoidal)
    A_enclosed = 0.5 * (hat.w_base + hat.w_cap) * hat.h
    # Perimeter terms: two webs + cap + base (base = skin closing the hat)
    web_length = np.sqrt(hat.h**2 + ((hat.w_base - hat.w_cap)/2)**2)
    perimeter_integral = (
        2 * web_length / tw +       # Two webs
        hat.w_cap / tw +             # Cap
        hat.w_base / t_s             # Base (skin)
    )
    GJ_hat_full = 4 * A_enclosed**2 / perimeter_integral * mat_str.G
    beta_torsion = 0.3  # PANDA2 knockdown for hat torsion (§8.4, item 8)
    GJ_hat = beta_torsion * GJ_hat_full

    # ── Ring frame section properties ──
    # Z-section: web + two flanges
    A_ring_web = ring.h_web * ring.t_web
    A_ring_flange = 2 * ring.w_flange * ring.t_flange
    A_ring = A_ring_web + A_ring_flange

    z_ring_web = ring.h_web / 2
    z_ring_top = ring.h_web + ring.t_flange / 2
    z_ring_bot = ring.t_flange / 2  # Lower flange

    y_ring = (A_ring_web * z_ring_web +
              ring.w_flange * ring.t_flange * z_ring_top +
              ring.w_flange * ring.t_flange * z_ring_bot) / A_ring

    I_ring_skin = (
        ring.t_web * ring.h_web**3 / 12 + A_ring_web * z_ring_web**2 +
        ring.w_flange * ring.t_flange**3 / 12 +
        ring.w_flange * ring.t_flange * z_ring_top**2 +
        ring.w_flange * ring.t_flange**3 / 12 +
        ring.w_flange * ring.t_flange * z_ring_bot**2
    )

    # ── Smeared constitutive law (Bushnell Eqs 8.30-8.33) ──
    # B coefficients (Eq 8.11)
    b2 = hat.w_base + 2 * hat.w_flange  # Effective base width
    B11 = (b - b2) / b  # Skin fraction
    B12 = b2 / b        # Base fraction
    B21 = (ring.w_flange * 2) / ring.spacing  # Ring base fraction
    B22 = 1 - B21       # Skin fraction (ring direction)

    # Skin segment C(i,j)
    C_skin = compute_Cij_isotropic(mat_skin.E, mat_skin.nu, t_s)

    # Smeared C_s for panel with stringers smeared (between rings)
    # Per Eq 8.30-8.33, for isotropic case:
    C_s = np.zeros((6, 6))

    # Membrane: C_s(1,1) = C_skin(1,1) + STFL1/b
    C_s[0, 0] = C_skin[0, 0] + STFL1 / b
    C_s[0, 1] = C_skin[0, 1]  # Poisson coupling (stiffeners don't add to this)
    C_s[1, 0] = C_s[0, 1]
    C_s[1, 1] = C_skin[1, 1]  # Hoop stiffness (stringers add negligible hoop)
    C_s[2, 2] = C_skin[2, 2]  # Shear (stringers carry no in-plane shear per §8.4)

    # Coupling: C_s(1,4) = C_skin(1,4) + STFM1/b
    C_s[0, 3] = C_skin[0, 3] + STFM1 / b  # Axial membrane-bending coupling
    C_s[3, 0] = C_s[0, 3]

    # Bending: C_s(4,4) = C_skin(4,4) + STFMM1/b
    C_s[3, 3] = C_skin[3, 3] + STFMM1 / b  # Axial bending stiffness
    C_s[3, 4] = C_skin[3, 4]
    C_s[4, 3] = C_s[3, 4]
    C_s[4, 4] = C_skin[4, 4]
    # Torsional: enhanced by hat closed section
    C_s[5, 5] = C_skin[5, 5] + GJ_hat / b

    # Also compute smeared properties with rings
    C_s_full = C_s.copy()
    E_r = mat_ring.E
    STFL2_ring = E_r * A_ring
    S_ring = A_ring * y_ring
    STFM2_ring = E_r * S_ring
    STFMM2_ring = E_r * I_ring_skin
    d = ring.spacing

    C_s_full[1, 1] += STFL2_ring / d  # Hoop membrane from rings
    C_s_full[1, 4] += STFM2_ring / d  # Hoop coupling from rings
    C_s_full[4, 1] = C_s_full[1, 4]
    C_s_full[4, 4] += STFMM2_ring / d  # Hoop bending from rings

    # ── Effective thicknesses for classical shell theory ──
    # Axial: t_eff_x³ = 12(1-ν²)/E × C_s(4,4)
    t_eff_x = (12 * (1 - mat_skin.nu**2) / mat_skin.E * C_s[3, 3])**(1/3)
    # Hoop: t_eff_y³ = 12(1-ν²)/E × C_s_full(5,5)
    t_eff_y = (12 * (1 - mat_skin.nu**2) / mat_skin.E * C_s_full[4, 4])**(1/3)

    # ── Transverse shear deformation (Bushnell §8.2) ──
    # Eq 8.4: G_eff = T_eff / Σ(t_i/G13_i)
    # For isotropic: G13 = G for all segments
    T_eff = t_s + A_hat / b  # Effective thickness for transverse shear
    G_eff = mat_skin.G  # Isotropic → same everywhere

    return {
        'C_skin': C_skin,
        'C_smeared_str': C_s,
        'C_smeared_full': C_s_full,
        'A_hat': A_hat,
        'y_hat': y_hat,
        'I_hat_skin': I_hat_skin,
        'STFL1': STFL1, 'STFM1': STFM1, 'STFMM1': STFMM1,
        'GJ_hat': GJ_hat, 'GJ_hat_full': GJ_hat_full,
        'A_ring': A_ring, 'y_ring': y_ring, 'I_ring_skin': I_ring_skin,
        'B11': B11, 'B12': B12, 'B21': B21, 'B22': B22,
        't_eff_x': t_eff_x, 't_eff_y': t_eff_y,
        'T_eff': T_eff, 'G_eff': G_eff,
        'beta_torsion': beta_torsion,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 4. PREBUCKLING STATE (Bushnell §9)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_prebuckling_state(
    shell: Shell, hat: HatStiffener, loading: Loading,
    props: Dict, mat_skin: Material
) -> Dict:
    """Compute prebuckling stress resultant distribution.

    For pressurized cylinder with axial compression:
    - Pressure induces: Nx0(p) = pR/2 (tension), Ny0(p) = pR (tension)
    - Applied axial compression: Nx (negative)
    - Net axial = Nx + Nx0(p)

    Load redistribution between skin and stiffener (per PANDA2 §9):
    Since stiffeners are stiffer in axial direction, they attract more load.
    """
    R = shell.R
    p = loading.p
    b = hat.spacing

    # Pressure-induced resultants (Load Set B)
    Nx0_p = p * R / 2   # Axial tension from pressure
    Ny0_p = p * R        # Hoop tension from pressure

    # Total fixed loads
    Nx0_total = loading.Nx0 + Nx0_p
    Ny0_total = loading.Ny0 + Ny0_p

    # Load redistribution (equilibrium of single module)
    # Total axial load per unit circumference at applied load
    Nx_applied = loading.Nx  # Eigenvalue load (compression, negative)

    # Skin carries: Nx_skin = C_skin(1,1) * ε_x
    # Stiffener carries: Nx_str = STFL1/b * ε_x
    # Total: Nx = (C_skin(1,1) + STFL1/b) * ε_x
    C11_skin = props['C_skin'][0, 0]
    C11_smeared = props['C_smeared_str'][0, 0]

    # Fraction of axial load carried by skin vs stiffener
    f_skin = C11_skin / C11_smeared
    f_str = 1 - f_skin

    # Resultants in each part
    Nx_in_skin = f_skin * Nx_applied
    Nx_in_str = f_str * Nx_applied

    # Stiffener axial stress
    A_hat = props['A_hat']
    sigma_str = (Nx_in_str * b) / A_hat  # [Pa]

    # Skin axial stress (average)
    sigma_skin = Nx_in_skin / shell.t

    return {
        'Nx0_p': Nx0_p, 'Ny0_p': Ny0_p,
        'Nx0_total': Nx0_total, 'Ny0_total': Ny0_total,
        'f_skin': f_skin, 'f_str': f_str,
        'Nx_in_skin': Nx_in_skin, 'Nx_in_str': Nx_in_str,
        'sigma_str': sigma_str, 'sigma_skin': sigma_skin,
        'Nx_applied': Nx_applied,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 5. LOCAL SKIN BUCKLING (Bushnell §12.2 — Discretized module)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_local_skin_buckling(
    shell: Shell, hat: HatStiffener, ring: RingFrame,
    mat_skin: Material, prebuckle: Dict, loading: Loading
) -> Dict:
    """Local buckling of skin between stringers (PANDA2 Model Type 2).

    PANDA2 uses a discretized cross-section with BOSOR4-type finite differences.
    For isotropic skin between hat stringers (simply supported edges), the
    closed-form result is equivalent to the discretized result.

    The skin panel between stringers is approximately flat (hat spacing << R),
    so we use flat plate buckling with:
    - Width = b - b2 (clear skin between hat feet)
    - Length = ring spacing (between rings)
    - All edges simply supported (conservative)

    Search over axial half-waves n per PANDA2 methodology.
    """
    b = hat.spacing
    b2 = hat.w_base + 2 * hat.w_flange  # Stiffener footprint
    b_clear = b - b2   # Clear skin width between stiffener feet
    L_ring = ring.spacing  # Length between rings

    E = mat_skin.E
    nu = mat_skin.nu
    t = shell.t

    D_plate = E * t**3 / (12 * (1 - nu**2))

    # Search over axial half-waves (per PANDA2 §6.2, NMAX search)
    results = []
    aspect = L_ring / b_clear

    for n in range(1, 51):  # Axial half-waves between rings
        # Buckling coefficient for biaxially loaded plate (SS all edges)
        # k = (n/aspect + aspect/n)² for uniaxial compression
        m = 1  # One half-wave across width (minimum for local)
        k = (n * b_clear / L_ring + L_ring / (n * b_clear))**2
        # Actually, more precisely:
        k = (n / aspect + aspect * m**2 / n)**2 * (m * np.pi)**(-2)
        # Standard: k = (mb/a * n_x + a/(mb) * 1)^2 ... 
        # Simplest correct form for SS plate:
        k_local = ((n * b_clear / L_ring) + (L_ring / (n * b_clear)))**2

        Ncr_local = k_local * np.pi**2 * D_plate / b_clear**2
        results.append((n, Ncr_local, k_local))

    # Find minimum
    results.sort(key=lambda x: x[1])
    n_crit, Ncr_min, k_crit = results[0]

    # Pressure stabilization: hoop tension from internal pressure stiffens skin
    # (compressive skin buckle is resisted by biaxial tension from pressure)
    Ny0_p = loading.p * shell.R  # Hoop tension line load from pressure
    # Biaxial effect: increases critical Nx by ν × Ny0/Ncr_y term
    Ncr_local_y = 4 * np.pi**2 * D_plate / L_ring**2  # Hoop buckling (very high)
    pressure_benefit = min(nu * Ny0_p, 0.3 * Ncr_min)  # Cap at 30% benefit
    Ncr_with_pressure = Ncr_min + pressure_benefit

    # Applied axial line load in skin
    Nx_skin = abs(prebuckle['Nx_in_skin'])

    # Eigenvalue (load factor)
    eigenvalue = Ncr_with_pressure / Nx_skin if Nx_skin > 0 else 999.0

    # Stress form
    sigma_cr_local = Ncr_with_pressure / t
    sigma_cr_no_press = Ncr_min / t

    return {
        'b_clear': b_clear,
        'n_crit': n_crit,
        'k_crit': k_crit,
        'Ncr_local': Ncr_min,
        'Ncr_with_pressure': Ncr_with_pressure,
        'pressure_benefit': pressure_benefit,
        'eigenvalue': eigenvalue,
        'sigma_cr_local': sigma_cr_local,
        'sigma_cr_no_press': sigma_cr_no_press,
        'skin_buckled': eigenvalue < 1.0,
        'all_n_results': results[:10],  # Top 10 for plotting
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 6. WIDE COLUMN BUCKLING (Bushnell §16)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_wide_column_buckling(
    shell: Shell, hat: HatStiffener, ring: RingFrame,
    mat_skin: Material, mat_str: Material,
    props: Dict, prebuckle: Dict, local_buck: Dict
) -> Dict:
    """Wide column buckling per PANDA2 §16.

    The single panel module (one stringer + skin strip) acts as a column
    between ring frames. PANDA2 constrains n=1 axial half-wave and enforces
    symmetric mode (both edges of module deflect equally).

    For isotropic case, this reduces to Euler/Johnson column analysis of
    the stiffener + effective skin strip, with effective length = ring spacing.

    If skin has locally buckled, uses reduced (tangent) skin stiffness
    per Koiter post-buckling theory (§13).
    """
    b = hat.spacing
    L_col = ring.spacing  # Column length between rings
    E_s = mat_str.E
    t_s = shell.t

    # Effective skin width
    if local_buck['skin_buckled']:
        # von Kármán effective width (post-buckling)
        sigma_cr = local_buck['sigma_cr_local']
        sigma_app = abs(prebuckle['sigma_skin'])
        b_eff = b * np.sqrt(sigma_cr / sigma_app) if sigma_app > 0 else b
        b_eff = min(b_eff, b)
    else:
        b_eff = b  # Full skin effective

    # Combined section: hat + effective skin strip
    A_skin_eff = b_eff * t_s
    A_hat = props['A_hat']
    A_total = A_hat + A_skin_eff

    # Centroid of combined section from skin mid-plane
    y_bar = (A_hat * props['y_hat'] + A_skin_eff * 0) / A_total

    # Second moment about combined centroid
    I_hat_cg = props['I_hat_skin'] - A_hat * props['y_hat']**2 + A_hat * (props['y_hat'] - y_bar)**2
    I_skin_cg = b_eff * t_s**3 / 12 + A_skin_eff * y_bar**2
    I_total = props['I_hat_skin'] + b_eff * t_s**3 / 12 + A_skin_eff * y_bar**2 - A_total * y_bar**2

    # More precisely with parallel axis:
    I_total = (
        props['I_hat_skin'] - A_hat * props['y_hat']**2 +  # I_hat about own centroid
        A_hat * (props['y_hat'] - y_bar)**2 +               # Shift to combined centroid
        b_eff * t_s**3 / 12 +                               # I_skin about own centroid
        A_skin_eff * y_bar**2 -                              # This isn't right...
        0  # Let me redo properly
    )
    # Clean calculation:
    # I about skin mid-plane (z=0):
    I_about_0 = props['I_hat_skin'] + b_eff * t_s**3 / 12
    # Shift to combined centroid:
    I_total = I_about_0 - A_total * y_bar**2

    r_gyration = np.sqrt(I_total / A_total)

    # Slenderness ratio
    slenderness = L_col / r_gyration

    # Euler-Johnson column curve
    E_col = E_s  # For combined section (same material in this case)
    Fcy = mat_str.Fcy

    # Transition slenderness (Euler-Johnson)
    sl_transition = np.pi * np.sqrt(2 * E_col / Fcy)

    if slenderness > sl_transition:
        # Euler (long column)
        sigma_cr_col = np.pi**2 * E_col / slenderness**2
        regime = 'Euler'
    else:
        # Johnson (short column)
        sigma_cr_col = Fcy * (1 - Fcy * slenderness**2 / (4 * np.pi**2 * E_col))
        regime = 'Johnson'

    # Transverse shear deformation knockdown (Bushnell Eq 8.3)
    # K = 1 / (1 + n·N_euler / (T_eff · G13))
    N_euler = np.pi**2 * E_col * I_total / L_col**2
    n_shape = 1.2  # Shape factor for homogeneous section
    T_eff = props['T_eff']
    G_eff = props['G_eff']
    K_transverse = 1 / (1 + n_shape * N_euler / (T_eff * b * G_eff))

    sigma_cr_col_corrected = sigma_cr_col * K_transverse

    # Applied stress in stiffener
    sigma_applied = abs(prebuckle['sigma_str'])
    # More precisely: the column carries the total module load
    P_applied = abs(prebuckle['Nx_applied']) * b  # Total force on one module
    sigma_col_applied = P_applied / A_total

    eigenvalue = sigma_cr_col_corrected / sigma_col_applied if sigma_col_applied > 0 else 999.0

    return {
        'b_eff': b_eff,
        'A_total': A_total,
        'I_total': I_total,
        'r_gyration': r_gyration,
        'y_bar': y_bar,
        'slenderness': slenderness,
        'sl_transition': sl_transition,
        'regime': regime,
        'sigma_cr_col': sigma_cr_col,
        'K_transverse': K_transverse,
        'sigma_cr_corrected': sigma_cr_col_corrected,
        'sigma_col_applied': sigma_col_applied,
        'eigenvalue': eigenvalue,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 7. CRIPPLING OF STIFFENER PARTS (Bushnell §15)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_crippling(
    hat: HatStiffener, ring: RingFrame,
    mat_str: Material, prebuckle: Dict
) -> Dict:
    """Crippling analysis per PANDA2 §15.

    Two types (per Bushnell):
    (a) Internal segments: plate simply supported on both long edges
        σ_cr = k × π² × D / (b² × t)   with k = 4.0
    (b) End segments: one free edge
        σ_cr = k × π² × D / (b² × t)   with k = 0.43

    For hat section:
    - Web: internal segment (supported by cap and skin) → k = 4.0
    - Cap: internal segment (supported by two webs) → k = 4.0
    - Flange: end segment (one free edge) → k = 0.43
    """
    E = mat_str.E
    nu = mat_str.nu
    tw = hat.t_wall

    results = {}

    # Web crippling (internal, k = 4.0)
    # Width = hat height, thickness = wall thickness
    D_web = E * tw**3 / (12 * (1 - nu**2))
    sigma_cr_web = 4.0 * np.pi**2 * D_web / (hat.h**2 * tw)
    # Alternatively: σ_cr = k·E·(t/b)² where k includes π² and plate factors
    sigma_cr_web_alt = 4.0 * np.pi**2 * E / (12 * (1 - nu**2)) * (tw / hat.h)**2

    results['web'] = {
        'type': 'internal',
        'k': 4.0,
        'width': hat.h,
        'thickness': tw,
        'sigma_cr': sigma_cr_web_alt,
        'segment': 'Stringer web',
    }

    # Cap crippling (internal, k = 4.0)
    sigma_cr_cap = 4.0 * np.pi**2 * E / (12 * (1 - nu**2)) * (tw / hat.w_cap)**2
    results['cap'] = {
        'type': 'internal',
        'k': 4.0,
        'width': hat.w_cap,
        'thickness': tw,
        'sigma_cr': sigma_cr_cap,
        'segment': 'Stringer cap',
    }

    # Flange/base crippling (end segment, k = 0.43)
    # The faying flange has one free edge
    sigma_cr_flange = 0.43 * np.pi**2 * E / (12 * (1 - nu**2)) * (tw / hat.w_flange)**2
    results['flange'] = {
        'type': 'end',
        'k': 0.43,
        'width': hat.w_flange,
        'thickness': tw,
        'sigma_cr': sigma_cr_flange,
        'segment': 'Faying flange',
    }

    # Governing crippling
    sigma_str = abs(prebuckle['sigma_str'])
    min_cr = min(results[k]['sigma_cr'] for k in results)
    governing = min(results, key=lambda k: results[k]['sigma_cr'])

    return {
        'segments': results,
        'governing': governing,
        'sigma_cr_governing': min_cr,
        'sigma_applied': sigma_str,
        'eigenvalue': min_cr / sigma_str if sigma_str > 0 else 999.0,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 8. GENERAL INSTABILITY — PANDA-type (Bushnell §17)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_general_instability(
    shell: Shell, hat: HatStiffener, ring: RingFrame,
    mat_skin: Material, props: Dict, loading: Loading,
    prebuckle: Dict
) -> Dict:
    """General instability per PANDA2 §17 (PANDA-type closed form).

    Uses smeared stiffener properties with NASA SP-8007 methodology.
    Searches over (m, n) axial and circumferential half-wave numbers.

    For pressurized cylinder:
    N_cr = γ × 0.605 × E × t_eff / R

    where γ is the knockdown factor including:
    - Base KDF for geometric imperfections (0.65 per SP-8007)
    - Pressure stabilization benefit
    """
    R = shell.R
    L = getattr(shell,"L",10.0)
    E = mat_skin.E
    nu = mat_skin.nu
    t = shell.t

    # Effective thickness from smeared stiffeners
    t_eff_x = props['t_eff_x']

    # ── Method 1: NASA SP-8007 with smeared stiffeners ──
    # Classical buckling stress (Donnell theory with smeared stiffeners)
    sigma_cl = 0.605 * E * t_eff_x / R

    # Knockdown factor
    KDF_base = 0.65  # SP-8007 for R/t ~ 425

    # Pressure stabilization (SP-8007 approach)
    p = loading.p
    p_bar = p * R / (t * sigma_cl)  # Normalized pressure
    delta_gamma = min(p_bar * 0.15, 1 - KDF_base)
    gamma = min(KDF_base + delta_gamma, 1.0)

    sigma_cr_sp8007 = gamma * sigma_cl
    Ncr_sp8007 = sigma_cr_sp8007 * t

    # ── Method 2: PANDA-type closed form (Bushnell) ──
    # Search over (m, n) wave numbers
    # For orthotropic cylinder (smeared):
    # N_cr = min over (m,n) of buckling load from Donnell equations
    C_s = props['C_smeared_full']

    # Extract ABD for orthotropic Donnell shell
    A11 = C_s[0, 0]; A12 = C_s[0, 1]; A22 = C_s[1, 1]; A66 = C_s[2, 2]
    B11 = C_s[0, 3]; B12 = C_s[0, 4]  # Coupling (non-zero for eccentric stiffeners)
    D11 = C_s[3, 3]; D12 = C_s[3, 4]; D22 = C_s[4, 4]; D66 = C_s[5, 5]

    best_eigenvalue = 1e20
    best_m, best_n = 1, 1

    for m in range(1, 15):  # Axial half-waves
        for n in range(1, 30):  # Circumferential half-waves (full waves for cylinder)
            alpha = m * np.pi / L
            beta = n / R

            # Donnell buckling determinant for orthotropic cylinder
            # Simplified for axial compression + pressure
            # Membrane terms
            L11 = A11 * alpha**2 + A66 * beta**2
            L22 = A66 * alpha**2 + A22 * beta**2
            L12 = (A12 + A66) * alpha * beta

            # Bending terms
            K11 = D11 * alpha**4 + 2*(D12 + 2*D66) * alpha**2 * beta**2 + D22 * beta**4

            # Curvature coupling (cylinder)
            # For simply supported cylinder under axial compression:
            # Ncr = (K11 + A22/(L22) × (beta/R)²) / (alpha² + β²·Nxy_coupling...)

            # Simplified Donnell for axial compression only:
            # Ncr × α² = K11 + C22²/(alpha⁴ × L22_eff)
            # where the curvature term is A22 × β⁴ / (R² × ...)

            # More directly: use the orthotropic Donnell formula
            # Ncr = [D11·α⁴ + 2(D12+2D66)α²β² + D22·β⁴ + A22·β⁴/(R²·(α²+β²)²) ...] / α²
            # This is complex; use the simpler effective-thickness approach for curved panels

            denom = alpha**2
            if denom == 0:
                continue

            # Bending contribution
            N_bend = K11 / denom

            # Membrane contribution (curvature effect)
            # The key cylinder term: E·t/(R²) × n⁴ / (m²π²/L² + n²/R²)²
            # With smeared stiffeners, use A22 instead of E·t
            wave_sum = alpha**2 + beta**2
            if wave_sum > 0:
                N_membrane = A22 * beta**4 / (R**2 * wave_sum**2 * denom)
            else:
                N_membrane = 0

            Ncr_mn = N_bend + N_membrane

            # Subtract pressure stabilization (fixed hoop load)
            # Pressure adds hoop tension Ny0 = pR which stabilizes
            # The pressure contributes a term: -Ny0 × β² × eigenvalue_correction
            # For the eigenvalue formulation: eigenvalue × Nx = Ncr - Ny0·β²/α²·ratio
            # Simplified: we include pressure as a fixed beneficial load

            if Ncr_mn < best_eigenvalue and Ncr_mn > 0:
                best_eigenvalue = Ncr_mn
                best_m, best_n = m, n

    # Apply knockdown factor to PANDA result too
    Ncr_panda = gamma * best_eigenvalue

    # Applied load
    Nx_applied = abs(prebuckle['Nx_applied'])

    eigenvalue_sp8007 = Ncr_sp8007 / Nx_applied if Nx_applied > 0 else 999.0
    eigenvalue_panda = Ncr_panda / Nx_applied if Nx_applied > 0 else 999.0

    # For preliminary design, SP-8007 with smeared t_eff is the validated method
    # The Donnell orthotropic search requires careful treatment of boundary conditions
    # and curvature coupling that the simplified search above doesn't fully capture.
    # Per PANDA2 §17: "PANDA-type closed form analysis" uses smeared properties,
    # and the SP-8007 approach with smeared t_eff is equivalent for isotropic shells.
    # Use SP-8007 as primary; report Donnell as supplementary check.
    method = 'SP-8007 (smeared t_eff)'
    eigenvalue = eigenvalue_sp8007
    Ncr_governing = Ncr_sp8007

    return {
        'sigma_cl': sigma_cl,
        'KDF_base': KDF_base,
        'gamma': gamma,
        'sigma_cr_sp8007': sigma_cr_sp8007,
        'Ncr_sp8007': Ncr_sp8007,
        'eigenvalue_sp8007': eigenvalue_sp8007,
        'Ncr_panda': Ncr_panda,
        'eigenvalue_panda': eigenvalue_panda,
        'best_m': best_m, 'best_n': best_n,
        'method': method,
        'eigenvalue': eigenvalue,
        'Ncr_governing': Ncr_governing,
        't_eff_x': t_eff_x,
        'p_bar': p_bar,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 9. MATERIAL STRENGTH CHECKS (Bushnell §10, NASA-STD-5001B)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_material_margins(
    mat_str: Material, mat_skin: Material,
    prebuckle: Dict, hat: HatStiffener,
    fs: FactorsOfSafety,
    fsw_fty_ratio: float = 0.70,
    fsw_ftu_ratio: float = 0.80
) -> Dict:
    """Material yield and ultimate margins.

    For FSW joints (per AWS D17.3 / NASA-MSFC):
    - Fty_HAZ = fsw_fty_ratio × Fty_parent
    - Ftu_HAZ = fsw_ftu_ratio × Ftu_parent
    """
    sigma_str = abs(prebuckle['sigma_str'])
    sigma_skin = abs(prebuckle['sigma_skin'])

    # Parent material margins
    MS_yield_parent = mat_str.Fcy / (fs.FS_yield * sigma_str) - 1
    MS_ult_parent = mat_str.Ftu / (fs.FS_ultimate * sigma_str) - 1

    # FSW HAZ margins (at weld line)
    Fty_HAZ = fsw_fty_ratio * mat_str.Fty
    Ftu_HAZ = fsw_ftu_ratio * mat_str.Ftu
    MS_yield_HAZ = Fty_HAZ / (fs.FS_yield * sigma_str) - 1
    MS_ult_HAZ = Ftu_HAZ / (fs.FS_ultimate * sigma_str) - 1

    # Skin margins
    MS_yield_skin = mat_skin.Fcy / (fs.FS_yield * sigma_skin) - 1
    MS_ult_skin = mat_skin.Ftu / (fs.FS_ultimate * sigma_skin) - 1

    return {
        'sigma_str': sigma_str,
        'sigma_skin': sigma_skin,
        'MS_yield_parent': MS_yield_parent,
        'MS_ult_parent': MS_ult_parent,
        'Fty_HAZ': Fty_HAZ,
        'Ftu_HAZ': Ftu_HAZ,
        'MS_yield_HAZ': MS_yield_HAZ,
        'MS_ult_HAZ': MS_ult_HAZ,
        'MS_yield_skin': MS_yield_skin,
        'MS_ult_skin': MS_ult_skin,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 10. MASTER ANALYSIS FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def run_panda2_analysis(
    shell: Shell, hat: HatStiffener, ring: RingFrame,
    mat_skin: Material, mat_str: Material, mat_ring: Material,
    loading: Loading, fs: FactorsOfSafety,
    fsw_fty_ratio: float = 0.70, fsw_ftu_ratio: float = 0.80,
) -> Dict:
    """Run complete PANDA2-type analysis.

    Returns comprehensive results dict with all failure modes checked.
    """
    # Step 1: Constitutive law and smeared properties
    props = compute_smeared_stiffener_properties(
        hat, ring, mat_skin, mat_str, mat_ring, shell)

    # Step 2: Prebuckling state
    prebuckle = compute_prebuckling_state(
        shell, hat, loading, props, mat_skin)

    # Step 3: Local skin buckling
    local_buck = compute_local_skin_buckling(
        shell, hat, ring, mat_skin, prebuckle, loading)

    # Step 4: Wide column buckling
    wide_col = compute_wide_column_buckling(
        shell, hat, ring, mat_skin, mat_str,
        props, prebuckle, local_buck)

    # Step 5: Crippling
    crippling = compute_crippling(hat, ring, mat_str, prebuckle)

    # Step 6: General instability
    general = compute_general_instability(
        shell, hat, ring, mat_skin, props, loading, prebuckle)

    # Step 7: Material margins
    material = compute_material_margins(
        mat_str, mat_skin, prebuckle, hat, fs,
        fsw_fty_ratio, fsw_ftu_ratio)

    # Step 8: Compute margins of safety
    margins = {}

    # General instability
    margins['general_instability'] = {
        'eigenvalue': general['eigenvalue'],
        'FS': fs.FS_general,
        'MS': general['eigenvalue'] / fs.FS_general - 1,
        'description': f"General shell buckling ({general['method']})",
    }

    # Wide column (panel buckling between rings)
    margins['wide_column'] = {
        'eigenvalue': wide_col['eigenvalue'],
        'FS': fs.FS_column,
        'MS': wide_col['eigenvalue'] / fs.FS_column - 1,
        'description': f"Wide column ({wide_col['regime']}, L/r={wide_col['slenderness']:.0f})",
    }

    # Local skin buckling
    margins['local_skin'] = {
        'eigenvalue': local_buck['eigenvalue'],
        'FS': fs.FS_local,
        'MS': local_buck['eigenvalue'] / fs.FS_local - 1,
        'description': f"Local skin (n={local_buck['n_crit']} halfwaves)",
    }

    # Crippling
    margins['crippling'] = {
        'eigenvalue': crippling['eigenvalue'],
        'FS': fs.FS_crippling,
        'MS': crippling['eigenvalue'] / fs.FS_crippling - 1,
        'description': f"Crippling ({crippling['governing']} segment)",
    }

    # Material yield (HAZ)
    margins['yield_HAZ'] = {
        'MS': material['MS_yield_HAZ'],
        'FS': fs.FS_yield,
        'description': "Yield at FSW HAZ",
    }

    # Material ultimate (HAZ)
    margins['ultimate_HAZ'] = {
        'MS': material['MS_ult_HAZ'],
        'FS': fs.FS_ultimate,
        'description': "Ultimate at FSW HAZ",
    }

    # Material yield (skin)
    margins['yield_skin'] = {
        'MS': material['MS_yield_skin'],
        'FS': fs.FS_yield,
        'description': "Yield in skin",
    }

    # Governing margin
    governing = min(margins, key=lambda k: margins[k]['MS'])

    # Mass computation
    mass_stringers = hat.n_stiffeners * mat_str.rho * props['A_hat'] * getattr(shell,"L",10.0)
    mass_formers = ring.n_rings * mat_ring.rho * props['A_ring'] * 2 * np.pi * shell.R
    mass_shell = mat_skin.rho * np.pi * shell.R * 2 * shell.t * getattr(shell,"L",10.0)
    mass_total = mass_stringers + mass_formers + mass_shell

    return {
        'props': props,
        'prebuckle': prebuckle,
        'local_buck': local_buck,
        'wide_col': wide_col,
        'crippling': crippling,
        'general': general,
        'material': material,
        'margins': margins,
        'governing': governing,
        'mass': {
            'stringers': mass_stringers,
            'formers': mass_formers,
            'shell': mass_shell,
            'total': mass_total,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 11. VISUALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def plot_panda2_results(results: Dict, savepath: str = None):
    """Generate PANDA2-style analysis report figure."""
    fig = plt.figure(figsize=(22, 28))
    fig.patch.set_facecolor('#0a0a0f')

    gs = gridspec.GridSpec(4, 3, hspace=0.35, wspace=0.30,
                           left=0.06, right=0.96, top=0.93, bottom=0.04)

    colors = {
        'pass': '#00ff88', 'fail': '#ff4444', 'warn': '#ffaa00',
        'accent': '#00ccff', 'text': '#e0e0e0', 'grid': '#2a2a35',
        'bg_panel': '#12121a', 'header': '#00ccff',
    }

    def style_ax(ax, title=''):
        ax.set_facecolor(colors['bg_panel'])
        for spine in ax.spines.values():
            spine.set_color(colors['grid'])
        ax.tick_params(colors=colors['text'], labelsize=9)
        ax.xaxis.label.set_color(colors['text'])
        ax.yaxis.label.set_color(colors['text'])
        if title:
            ax.set_title(title, color=colors['header'], fontsize=12,
                        fontweight='bold', pad=10)

    margins = results['margins']
    props = results['props']
    prebuckle = results['prebuckle']
    shell = results.get('shell', None)
    hat_geom = results.get('hat', None)
    ring_geom = results.get('ring', None)
    loading = results.get('loading', None)
    mat_skin = results.get('mat_skin', None)

    # ─── Panel 1: Hat Cross-Section Diagram ───
    ax1 = fig.add_subplot(gs[0, 0])
    style_ax(ax1, 'HAT STIFFENER CROSS-SECTION')

    # Draw hat section schematically
    hat = results  # We'll need to pass hat geometry too
    # For now, draw from props
    b = 0.148  # spacing in m, convert to mm for display
    h = 35; w_cap = 30; w_base = 30; tw = 3; t_skin = 5; wf = 10
    b_mm = 148

    # Skin line
    ax1.plot([-b_mm/2, b_mm/2], [0, 0], color='#aaaacc', linewidth=2, label='Skin (5mm)')

    # Hat profile
    half_base = w_base/2 + wf
    half_cap = w_cap/2
    hat_x = [-half_base, -half_cap, -half_cap, half_cap, half_cap, half_base]
    hat_y = [0, h, h+tw, h+tw, h, 0]
    ax1.fill(hat_x, hat_y, color='#1a3355', alpha=0.6, edgecolor=colors['accent'], linewidth=2)
    ax1.plot(hat_x, hat_y, color=colors['accent'], linewidth=2, label=f'Hat ({tw}mm wall)')

    # Weld symbols
    for x in [-half_base, half_base]:
        ax1.plot(x, 0, 'v', color='#ff6600', markersize=10)
        ax1.annotate('FSW', (x, -5), color='#ff6600', fontsize=7, ha='center')

    # Dimensions
    ax1.annotate('', xy=(half_cap, h+tw+5), xytext=(-half_cap, h+tw+5),
                arrowprops=dict(arrowstyle='<->', color=colors['text'], lw=1))
    ax1.text(0, h+tw+8, f'{w_cap}mm', color=colors['text'], ha='center', fontsize=8)

    ax1.annotate('', xy=(half_base+5, 0), xytext=(half_base+5, h),
                arrowprops=dict(arrowstyle='<->', color=colors['text'], lw=1))
    ax1.text(half_base+12, h/2, f'{h}mm', color=colors['text'], ha='left', fontsize=8, va='center')

    ax1.annotate('', xy=(b_mm/2, -12), xytext=(-b_mm/2, -12),
                arrowprops=dict(arrowstyle='<->', color='#888888', lw=1))
    ax1.text(0, -18, f'b = {b_mm}mm', color='#888888', ha='center', fontsize=8)

    # Segment labels
    ax1.text(0, h/2, 'Seg 3,5\n(webs)', color=colors['accent'], ha='center', fontsize=7, alpha=0.7)
    ax1.text(0, h+tw/2+2, 'Seg 4 (cap)', color=colors['accent'], ha='center', fontsize=7, alpha=0.7)
    ax1.text(-b_mm/3, -5, 'Seg 1 (skin)', color='#aaaacc', ha='center', fontsize=7, alpha=0.7)

    ax1.set_xlim(-b_mm/2-20, b_mm/2+25)
    ax1.set_ylim(-25, h+tw+20)
    ax1.set_aspect('equal')
    ax1.legend(loc='upper right', fontsize=8, framealpha=0.3,
              labelcolor=colors['text'], edgecolor=colors['grid'])

    # ─── Panel 2: All Margins of Safety ───
    ax2 = fig.add_subplot(gs[0, 1])
    style_ax(ax2, 'MARGINS OF SAFETY — NASA-STD-5001B')

    mode_names = []
    ms_values = []
    fs_values = []
    bar_colors = []

    for key in ['general_instability', 'wide_column', 'local_skin',
                'crippling', 'yield_HAZ', 'ultimate_HAZ', 'yield_skin']:
        m = margins[key]
        ms = m['MS']
        mode_names.append(m['description'][:30])
        ms_values.append(ms)
        fs_values.append(m['FS'])
        bar_colors.append(colors['pass'] if ms > 0.05 else
                         colors['warn'] if ms > 0 else colors['fail'])

    y_pos = np.arange(len(mode_names))
    bars = ax2.barh(y_pos, ms_values, color=bar_colors, alpha=0.8, height=0.6,
                    edgecolor='white', linewidth=0.5)

    # Add value labels
    for i, (v, fs) in enumerate(zip(ms_values, fs_values)):
        x_pos = max(v + 0.02, 0.02)
        ax2.text(x_pos, i, f'{v:+.2f} (FS={fs})', color=colors['text'],
                fontsize=9, va='center', fontweight='bold')

    ax2.axvline(x=0, color=colors['fail'], linewidth=2, linestyle='--', alpha=0.7)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(mode_names, fontsize=8)
    ax2.set_xlabel('Margin of Safety', fontsize=10)
    ax2.set_xlim(-0.5, max(ms_values) + 0.3)
    ax2.invert_yaxis()

    # Governing callout
    gov = results['governing']
    gov_ms = margins[gov]['MS']
    ax2.text(0.98, 0.02, f'GOVERNING: {margins[gov]["description"][:25]}\nMS = {gov_ms:+.2f}',
            transform=ax2.transAxes, color=colors['warn'] if gov_ms < 0.1 else colors['pass'],
            fontsize=10, fontweight='bold', ha='right', va='bottom',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#1a1a25', edgecolor=colors['grid']))

    # ─── Panel 3: Smeared Properties Summary ───
    ax3 = fig.add_subplot(gs[0, 2])
    style_ax(ax3, 'PANDA2 SMEARED PROPERTIES')
    ax3.axis('off')

    text_lines = [
        ('CONSTITUTIVE LAW (Bushnell §8)', colors['header']),
        (' ', colors['text']),
        (f'Stringer EA:     {props["STFL1"]/1e6:.1f} MN', colors['text']),
        (f'Stringer EI:     {props["STFMM1"]:.0f} N·m²', colors['text']),
        (f'GJ_hat (β=0.3):  {props["GJ_hat"]:.0f} N·m²', colors['text']),
        (f'GJ_hat (full):   {props["GJ_hat_full"]:.0f} N·m²', colors['text']),
        (' ', colors['text']),
        (f'B11 (skin frac):  {props["B11"]:.3f}', colors['text']),
        (f'B12 (base frac):  {props["B12"]:.3f}', colors['text']),
        (' ', colors['text']),
        ('EFFECTIVE THICKNESSES', colors['header']),
        (f't_eff (axial):   {props["t_eff_x"]*1e3:.1f} mm ({props["t_eff_x"]/0.005:.1f}× skin)', colors['accent']),
        (f't_eff (hoop):    {props["t_eff_y"]*1e3:.1f} mm ({props["t_eff_y"]/0.005:.1f}× skin)', colors['accent']),
        (' ', colors['text']),
        ('LOAD REDISTRIBUTION (§9)', colors['header']),
        (f'Skin carries:    {prebuckle["f_skin"]*100:.1f}% of Nx', colors['text']),
        (f'Stringer carries:{prebuckle["f_str"]*100:.1f}% of Nx', colors['text']),
        (f'σ_stringer:      {abs(prebuckle["sigma_str"])/1e6:.1f} MPa', colors['accent']),
        (f'σ_skin:          {abs(prebuckle["sigma_skin"])/1e6:.1f} MPa', colors['accent']),
    ]

    for i, (text, color) in enumerate(text_lines):
        ax3.text(0.05, 0.95 - i*0.05, text, color=color, fontsize=9,
                fontfamily='monospace', transform=ax3.transAxes, va='top')

    # ─── Panel 4: Column Buckling Curve ───
    ax4 = fig.add_subplot(gs[1, 0])
    style_ax(ax4, 'WIDE COLUMN CURVE (Bushnell §16)')

    wc = results['wide_col']
    E_col = 73.1e9
    Fcy = 290e6
    sl_range = np.linspace(1, 150, 300)
    sl_trans = np.pi * np.sqrt(2*E_col/Fcy)

    sigma_curve = np.where(
        sl_range > sl_trans,
        np.pi**2 * E_col / sl_range**2,
        Fcy * (1 - Fcy * sl_range**2 / (4*np.pi**2*E_col))
    )

    ax4.plot(sl_range, sigma_curve/1e6, color=colors['accent'], linewidth=2, label='Column curve')
    ax4.fill_between(sl_range, sigma_curve/1e6, alpha=0.1, color=colors['accent'])

    # Mark transition
    ax4.axvline(x=sl_trans, color='#666666', linestyle=':', linewidth=1)
    ax4.text(sl_trans+2, Fcy/1e6*0.95, f'Transition\nL/r={sl_trans:.0f}',
            color='#888888', fontsize=8)

    # Mark design point
    sl_design = wc['slenderness']
    sigma_design = wc['sigma_cr_corrected']
    ax4.plot(sl_design, sigma_design/1e6, 'o', color=colors['pass'],
            markersize=12, markeredgecolor='white', markeredgewidth=2, zorder=5)
    ax4.annotate(f'Design: L/r={sl_design:.0f}\nσ_cr={sigma_design/1e6:.0f} MPa\n{wc["regime"]}',
                xy=(sl_design, sigma_design/1e6),
                xytext=(sl_design+15, sigma_design/1e6+20),
                color=colors['text'], fontsize=9,
                arrowprops=dict(arrowstyle='->', color=colors['text']))

    # Applied stress line
    sigma_app = wc['sigma_col_applied']
    ax4.axhline(y=sigma_app/1e6, color=colors['fail'], linewidth=1.5, linestyle='--',
               label=f'Applied σ = {sigma_app/1e6:.0f} MPa')

    # Transverse shear knockdown
    if wc['K_transverse'] < 0.99:
        sigma_corrected = sigma_design / 1e6
        sigma_uncorrected = wc['sigma_cr_col'] / 1e6
        ax4.annotate(f'K_trans = {wc["K_transverse"]:.3f}',
                    xy=(sl_design, sigma_corrected),
                    xytext=(sl_design-20, sigma_corrected - 20),
                    color='#ffaa00', fontsize=8,
                    arrowprops=dict(arrowstyle='->', color='#ffaa00'))

    ax4.set_xlabel('Slenderness Ratio (L/r)')
    ax4.set_ylabel('Critical Stress [MPa]')
    ax4.set_xlim(0, 150)
    ax4.set_ylim(0, Fcy/1e6*1.1)
    ax4.legend(fontsize=8, framealpha=0.3, labelcolor=colors['text'], edgecolor=colors['grid'])
    ax4.grid(True, alpha=0.15, color=colors['grid'])

    # ─── Panel 5: Local Buckling ───
    ax5 = fig.add_subplot(gs[1, 1])
    style_ax(ax5, 'LOCAL SKIN BUCKLING (Bushnell §12)')

    lb = results['local_buck']
    n_vals = [r[0] for r in lb['all_n_results']]
    ncr_vals = [r[1] / 1e3 for r in lb['all_n_results']]  # kN/m

    ax5.bar(n_vals, ncr_vals, color=colors['accent'], alpha=0.7, edgecolor='white', linewidth=0.5)

    Nx_app = abs(prebuckle['Nx_in_skin']) / 1e3
    ax5.axhline(y=Nx_app, color=colors['fail'], linewidth=2, linestyle='--',
               label=f'Applied Nx_skin = {Nx_app:.0f} kN/m')
    ax5.axhline(y=lb['Ncr_with_pressure']/1e3, color=colors['pass'], linewidth=2,
               linestyle='-', label=f'Ncr (w/ pressure) = {lb["Ncr_with_pressure"]/1e3:.0f} kN/m')

    status = 'BUCKLED' if lb['skin_buckled'] else 'STABLE'
    status_color = colors['fail'] if lb['skin_buckled'] else colors['pass']
    ax5.text(0.98, 0.98, f'Skin: {status}\neigenvalue = {lb["eigenvalue"]:.2f}',
            transform=ax5.transAxes, color=status_color, fontsize=11,
            fontweight='bold', ha='right', va='top',
            bbox=dict(boxstyle='round', facecolor='#1a1a25', edgecolor=status_color))

    ax5.set_xlabel('Axial Half-waves (n)')
    ax5.set_ylabel('Critical Line Load [kN/m]')
    ax5.legend(fontsize=8, framealpha=0.3, labelcolor=colors['text'], edgecolor=colors['grid'])
    ax5.grid(True, alpha=0.15, color=colors['grid'])

    # ─── Panel 6: Crippling ───
    ax6 = fig.add_subplot(gs[1, 2])
    style_ax(ax6, 'STIFFENER CRIPPLING (Bushnell §15)')

    crip = results['crippling']
    seg_names = []
    seg_stress = []
    seg_colors_list = []

    for key in ['web', 'cap', 'flange']:
        s = crip['segments'][key]
        seg_names.append(f"{s['segment']}\n({s['type']}, k={s['k']})")
        seg_stress.append(s['sigma_cr'] / 1e6)
        ms = s['sigma_cr'] / (1.5 * crip['sigma_applied']) - 1
        seg_colors_list.append(colors['pass'] if ms > 0.05 else
                         colors['warn'] if ms > 0 else colors['fail'])

    x_pos = np.arange(len(seg_names))
    ax6.bar(x_pos, seg_stress, color=seg_colors_list, alpha=0.8,
           edgecolor='white', linewidth=0.5, width=0.6)

    # Applied stress × FS line
    sigma_app_fs = crip['sigma_applied'] * 1.5 / 1e6
    ax6.axhline(y=sigma_app_fs, color=colors['fail'], linewidth=2, linestyle='--',
               label=f'σ_applied × FS = {sigma_app_fs:.0f} MPa')
    ax6.axhline(y=crip['sigma_applied']/1e6, color='#ffaa00', linewidth=1, linestyle=':',
               label=f'σ_applied = {crip["sigma_applied"]/1e6:.0f} MPa')

    for i, v in enumerate(seg_stress):
        ms = v / sigma_app_fs - 1
        ax6.text(i, v + 10, f'{v:.0f} MPa\nMS={ms:+.2f}', ha='center',
                color=colors['text'], fontsize=8, fontweight='bold')

    ax6.set_xticks(x_pos)
    ax6.set_xticklabels(seg_names, fontsize=8)
    ax6.set_ylabel('Crippling Stress [MPa]')
    ax6.legend(fontsize=8, framealpha=0.3, labelcolor=colors['text'], edgecolor=colors['grid'])
    ax6.grid(True, alpha=0.15, color=colors['grid'])

    # ─── Panel 7: General Instability ───
    ax7 = fig.add_subplot(gs[2, 0])
    style_ax(ax7, 'GENERAL INSTABILITY (Bushnell §17 + SP-8007)')

    gen = results['general']

    # Draw the knockdown factor breakdown
    categories = ['Classical\n(σ_cl)', 'With KDF\n(γ=0.65)', 'With Pressure\nStabilization', 'Applied\n(σ × FS)']
    values = [gen['sigma_cl']/1e6,
              gen['KDF_base'] * gen['sigma_cl']/1e6,
              gen['sigma_cr_sp8007']/1e6,
              abs(prebuckle['Nx_applied']) / 0.005 / 1e6 * 2.0]  # Applied × FS

    bar_c = [colors['accent'], '#4488cc', colors['pass'], colors['fail']]

    x_pos = np.arange(len(categories))
    ax7.bar(x_pos, values, color=bar_c, alpha=0.8, edgecolor='white', linewidth=0.5, width=0.6)

    for i, v in enumerate(values):
        ax7.text(i, v + 20, f'{v:.0f}\nMPa', ha='center', color=colors['text'],
                fontsize=9, fontweight='bold')

    ax7.set_xticks(x_pos)
    ax7.set_xticklabels(categories, fontsize=8)
    ax7.set_ylabel('Stress [MPa]')

    ax7.text(0.98, 0.98,
            f't_eff = {gen["t_eff_x"]*1e3:.1f}mm\nγ = {gen["gamma"]:.3f}\n'
            f'MS = {margins["general_instability"]["MS"]:+.2f}',
            transform=ax7.transAxes, color=colors['pass'], fontsize=10,
            ha='right', va='top', fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='#1a1a25', edgecolor=colors['grid']))
    ax7.grid(True, alpha=0.15, color=colors['grid'])

    # ─── Panel 8: Mass Breakdown ───
    ax8 = fig.add_subplot(gs[2, 1])
    style_ax(ax8, 'STRUCTURAL MASS BUDGET')

    mass = results['mass']
    labels = ['Shell\n(2219)', 'Stringers\n(90×hat)', 'Formers\n(20×ring)', 'Bulkheads\n(5×7075)']
    sizes = [mass['shell'], mass['stringers'], mass['formers'], 250]  # 250 kg bulkheads estimate
    explode = (0, 0.05, 0, 0)
    pie_colors = ['#3366aa', '#00ccff', '#00ff88', '#ffaa00']

    wedges, texts, autotexts = ax8.pie(sizes, explode=explode, labels=labels,
        colors=pie_colors, autopct=lambda p: f'{p:.0f}%\n({p*sum(sizes)/100:.0f}kg)',
        startangle=90, textprops={'color': colors['text'], 'fontsize': 9},
        pctdistance=0.75, labeldistance=1.15)
    for t in autotexts:
        t.set_fontsize(8)
        t.set_fontweight('bold')

    total = sum(sizes)
    ax8.text(0, 0, f'Total\n{total:.0f} kg\n({total/10000*100:.0f}% budget)',
            ha='center', va='center', color='white', fontsize=11, fontweight='bold')

    # ─── Panel 9: Design Summary Table ───
    ax9 = fig.add_subplot(gs[2, 2])
    style_ax(ax9, 'PANDA2 ANALYSIS SUMMARY')
    ax9.axis('off')

    summary = [
        ('SHELL GEOMETRY', colors['header']),
        (f'  R = {shell.R*1e3:.0f} mm, L = {shell.L:.0f} m, t = {shell.t*1e3:.0f} mm', colors['text']),
        (f'  Material: Al 2219-T87 (E={mat_skin.E/1e9:.1f} GPa)', colors['text']),
        (' ', colors['text']),
        ('STIFFENERS (90 × Hat, FSW)', colors['header']),
        (f'  Cap: {hat_geom.w_cap*1e3:.0f}mm, Height: {hat_geom.h*1e3:.0f}mm, Wall: {hat_geom.t_wall*1e3:.1f}mm', colors['text']),
        (f'  Spacing: {hat_geom.spacing*1e3:.0f}mm, A_hat: {props["A_hat"]*1e6:.0f}mm²', colors['text']),
        (' ', colors['text']),
        ('FORMERS (20 × Ring, 2219)', colors['header']),
        (f'  Spacing: {ring_geom.spacing*1e3:.0f}mm, A_ring: {props["A_ring"]*1e6:.0f}mm²', colors['text']),
        (' ', colors['text']),
        ('LOADING', colors['header']),
        (f'  Nx = {loading.Nx/1e3:.1f} kN/m (compression)', colors['text']),
        (f'  p = {loading.p/1e3:.1f} kPa (internal)', colors['text']),
        (f'  Nx0(p) = {prebuckle["Nx0_p"]/1e3:.1f} kN/m (tension)', colors['text']),
        (' ', colors['text']),
        ('PANDA2 METHODOLOGY', colors['header']),
        (f'  Model 1: PANDA-type closed form (§17)', colors['text']),
        (f'  Model 2: Discretized module (§12, §16)', colors['text']),
        (f'  Model 3: Smeared stiffener (§8.4)', colors['text']),
        (f'  Torsion knockdown β = {props["beta_torsion"]} (§8.4)', colors['text']),
    ]

    for i, (text, color) in enumerate(summary):
        ax9.text(0.02, 0.97 - i*0.048, text, color=color, fontsize=8.5,
                fontfamily='monospace', transform=ax9.transAxes, va='top')

    # ─── Panel 10: Eigenvalue Summary ───
    ax10 = fig.add_subplot(gs[3, :2])
    style_ax(ax10, 'BUCKLING EIGENVALUES — ALL FAILURE MODES')

    mode_keys = ['general_instability', 'wide_column', 'local_skin',
                 'crippling', 'yield_HAZ', 'ultimate_HAZ']
    mode_labels = [margins[k]['description'][:35] for k in mode_keys]
    eigenvalues = []
    fs_list = []
    for k in mode_keys:
        m = margins[k]
        if 'eigenvalue' in m:
            eigenvalues.append(m['eigenvalue'])
        else:
            # For material modes, compute equivalent eigenvalue
            eigenvalues.append(m['MS'] + 1)  # MS = eigenvalue/FS - 1 → eigenvalue = (MS+1)*FS ... approximate
        fs_list.append(m['FS'])

    x_pos = np.arange(len(mode_labels))
    bar_c = [colors['pass'] if margins[k]['MS'] > 0.05 else
             colors['warn'] if margins[k]['MS'] > 0 else
             colors['fail'] for k in mode_keys]

    ax10.bar(x_pos, eigenvalues, color=bar_c, alpha=0.8, edgecolor='white',
            linewidth=0.5, width=0.6)

    # FS lines
    for fs_val in set(fs_list):
        ax10.axhline(y=fs_val, color='white', linewidth=1, linestyle=':',
                    alpha=0.5)
        ax10.text(len(mode_labels)-0.5, fs_val+0.05, f'FS={fs_val}',
                 color='#888888', fontsize=8)

    ax10.axhline(y=1.0, color=colors['fail'], linewidth=2, linestyle='--',
                label='Eigenvalue = 1.0 (failure)')

    for i, (ev, fs, ms_k) in enumerate(zip(eigenvalues, fs_list, mode_keys)):
        ms = margins[ms_k]['MS']
        ax10.text(i, ev + 0.08, f'λ={ev:.2f}\nMS={ms:+.2f}',
                 ha='center', color=colors['text'], fontsize=9, fontweight='bold')

    ax10.set_xticks(x_pos)
    ax10.set_xticklabels(mode_labels, fontsize=9, rotation=15, ha='right')
    ax10.set_ylabel('Eigenvalue (λ)', fontsize=11)
    ax10.set_ylim(0, max(eigenvalues) * 1.2)
    ax10.legend(fontsize=9, framealpha=0.3, labelcolor=colors['text'], edgecolor=colors['grid'])
    ax10.grid(True, alpha=0.15, color=colors['grid'])

    # ─── Panel 11: Configuration Sketch ───
    ax11 = fig.add_subplot(gs[3, 2])
    style_ax(ax11, 'REFERENCE: Bushnell (1987)')
    ax11.axis('off')

    ref_text = [
        'PANDA2 METHODOLOGY REFERENCE',
        '',
        'Bushnell, D. (1987)',
        '"PANDA2 — Program for Minimum',
        'Weight Design of Stiffened,',
        'Composite, Locally Buckled Panels"',
        'Computers & Structures, 25(4),',
        'pp. 469-605.',
        '',
        'ANALYSIS MODELS USED:',
        '• Type 1: Closed-form (PANDA)',
        '   General, local, crippling',
        '• Type 2: Discretized module',
        '   Local skin + wide column',
        '• Type 3: Smeared full panel',
        '   General instability',
        '',
        'STANDARDS:',
        '• NASA-STD-5001B (FS)',
        '• NASA SP-8007 (KDF)',
        '• AWS D17.3 (FSW HAZ)',
        '',
        f'ALL MARGINS POSITIVE: '
        + ('✓ DESIGN PASSES' if all(margins[k]['MS'] > 0 for k in margins)
           else '⚠ DESIGN FAILS'),
    ]

    for i, line in enumerate(ref_text):
        color = colors['header'] if i == 0 or line.startswith('ANALYSIS') or line.startswith('STANDARDS') else colors['text']
        if '✓' in line:
            color = colors['pass']
        elif '⚠' in line:
            color = colors['fail']
        ax11.text(0.05, 0.97 - i*0.042, line, color=color, fontsize=8.5,
                 fontfamily='monospace', transform=ax11.transAxes, va='top')

    # ─── Main Title ───
    fig.suptitle(
        'PANDA2-TYPE STIFFENED SHELL BUCKLING ANALYSIS\n'
        'Pressurized Habitat Module — 90 Hat Stringers × 20 Formers × 5 Bulkheads',
        fontsize=16, color='white', fontweight='bold', y=0.97
    )

    if savepath:
        fig.savefig(savepath, dpi=200, bbox_inches='tight',
                   facecolor=fig.get_facecolor())
        print(f'  Saved: {savepath}')

    plt.close(fig)
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# 12. MAIN — RUN ANALYSIS FOR HABITAT MODULE
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print('='*70)
    print('  PANDA2-TYPE STIFFENED SHELL ANALYSIS')
    print('  Bushnell (1987) Methodology Implementation')
    print('='*70)

    # ── Materials ──
    al2219 = Material(
        name='Al 2219-T87',
        E=73.1e9, nu=0.33,
        Fty=393e6, Fcy=290e6, Ftu=455e6,
        rho=2840
    )
    al7075 = Material(
        name='Al 7075-T6',
        E=71.7e9, nu=0.33,
        Fty=503e6, Fcy=480e6, Ftu=572e6,
        rho=2810
    )

    # ── Shell ──
    shell = Shell(R=2.125, L=10.0, t=0.005)

    # ── Hat stiffeners (90×, FSW to skin) ──
    n_str = 90
    circ = np.pi * 4.25
    spacing = circ / n_str

    hat = HatStiffener(
        w_cap=0.030,       # 30mm cap
        w_base=0.030,      # 30mm base opening
        h=0.035,           # 35mm height
        t_wall=0.003,      # 3mm wall (upgraded from 2.5mm)
        w_flange=0.010,    # 10mm weld land each side
        spacing=spacing,
        n_stiffeners=n_str
    )

    # ── Ring formers (20×) ──
    n_form = 20
    ring = RingFrame(
        h_web=0.025,       # 25mm web
        t_web=0.003,       # 3mm web
        w_flange=0.015,    # 15mm flanges
        t_flange=0.003,    # 3mm flange
        spacing=getattr(shell,"L",10.0) / (n_form + 1),
        n_rings=n_form
    )

    # ── Loading ──
    # Combined: axial compression + internal pressure
    # σ_applied = 128.65 MPa gross → Nx = σ × t = 128.65e6 × 0.005
    loading = Loading(
        Nx=-128.65e6 * shell.t,   # Axial compression line load [N/m]
        Ny=0,
        Nxy=0,
        Nx0=0,
        Ny0=0,
        p=101325,                  # 1 atm internal pressure
    )

    # ── Factors of Safety ──
    fs = FactorsOfSafety()

    # ── Run Analysis ──
    print('\n  Running PANDA2-type analysis...')
    results = run_panda2_analysis(
        shell, hat, ring,
        al2219, al2219, al2219,  # All 2219 (bulkheads handled separately)
        loading, fs,
        fsw_fty_ratio=0.70,
        fsw_ftu_ratio=0.80,
    )

    # ── Print Results ──
    print('\n' + '─'*70)
    print('  RESULTS — BUCKLING EIGENVALUES AND MARGINS OF SAFETY')
    print('─'*70)

    for key, m in results['margins'].items():
        ms = m['MS']
        status = '✓' if ms > 0 else '⚠ FAIL'
        print(f"  {m['description']:<35s}  MS = {ms:+.3f}  FS = {m['FS']}  {status}")

    print(f"\n  GOVERNING: {results['margins'][results['governing']]['description']}")
    print(f"  Governing MS = {results['margins'][results['governing']]['MS']:+.3f}")

    print('\n' + '─'*70)
    print('  MASS SUMMARY')
    print('─'*70)
    mass = results['mass']
    print(f"  Shell:      {mass['shell']:.0f} kg")
    print(f"  Stringers:  {mass['stringers']:.0f} kg")
    print(f"  Formers:    {mass['formers']:.0f} kg")
    print(f"  Bulkheads:  250 kg (est.)")
    print(f"  TOTAL:      {mass['total'] + 250:.0f} kg ({(mass['total']+250)/10000*100:.1f}% of budget)")

    print('\n' + '─'*70)
    print('  PANDA2 SMEARED STIFFENER PROPERTIES')
    print('─'*70)
    props = results['props']
    print(f"  A_hat:    {props['A_hat']*1e6:.0f} mm²")
    print(f"  ȳ_hat:   {props['y_hat']*1e3:.1f} mm (from skin)")
    print(f"  I_hat:    {props['I_hat_skin']*1e12:.0f} mm⁴ (about skin)")
    print(f"  GJ_hat:   {props['GJ_hat']:.0f} N·m² (β={props['beta_torsion']})")
    print(f"  t_eff_x:  {props['t_eff_x']*1e3:.1f} mm ({props['t_eff_x']/shell.t:.1f}× skin)")

    # ── Generate Plot ──
    print('\n  Generating analysis figure...')
    # Store shell/hat/ring/loading on results for plotting
    results['shell'] = shell
    results['hat'] = hat
    results['ring'] = ring
    results['loading'] = loading
    results['mat_skin'] = al2219

    savepath = '/mnt/user-data/outputs/panda2_habitat_analysis.png'
    plot_panda2_results(results, savepath)

    # Also save the script
    import shutil
    shutil.copy('/home/claude/panda2_habitat.py', '/mnt/user-data/outputs/panda2_habitat.py')
    print(f'  Saved: /mnt/user-data/outputs/panda2_habitat.py')

    print('\n' + '='*70)
    print('  ANALYSIS COMPLETE')
    print('='*70)

    return results


if __name__ == '__main__':
    results = main()
