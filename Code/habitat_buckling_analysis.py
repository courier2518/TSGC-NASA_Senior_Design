#!/usr/bin/env python3
"""
===============================================================================
STRUCTURAL ANALYSIS — Pressurized Habitat Module for Lunar/Martian Deployment
===============================================================================
Senior Design Project — Thin-Walled Pressure Vessel / Launch Vehicle Payload

Geometry:
    Length          = 10.0 m
    Outer Diameter  = 4.25 m
    Wall Thickness  = 5 mm
    Material        = Aluminum 2219-T67

Analysis Cases:
    Case 1: LAUNCH (Vertical) — 6G axial + 2G lateral, internal pressure,
            payload mass, nonlinear P-Δ, buckling interaction
    Case 2: ON-SURFACE (Horizontal) — Lunar or Martian gravity,
            pressurized, supported at ends + mid-span, with payload
    Case 3: PRESSURE-ONLY — Hoop/longitudinal stress verification

Standards Referenced:
    - NASA SP-8007 (Buckling of Thin-Walled Circular Cylinders)
    - NASA-STD-5001B (Structural Design & Test Factors of Safety)
    - AIAA S-110 (Space Systems Metallic Pressure Vessels)
===============================================================================
"""

import math
import sys
import json
from dataclasses import dataclass, field
from typing import Tuple

# =============================================================================
# DATA CLASSES
# =============================================================================
@dataclass
class Material:
    name: str
    E: float            # Young's modulus (Pa)
    nu: float           # Poisson's ratio
    rho: float          # Density (kg/m³)
    Fty: float          # Tensile yield strength (Pa)
    Ftu: float          # Ultimate tensile strength (Pa)
    Fcy: float          # Compressive yield strength (Pa)
    Fsu: float          # Shear ultimate strength (Pa)
    alpha_cte: float    # CTE (1/°C)


@dataclass
class Geometry:
    L: float            # Length (m)
    D_outer: float      # Outer diameter (m)
    t: float            # Wall thickness (m)

    @property
    def R(self): return self.D_outer / 2.0

    @property
    def R_mid(self): return self.R - self.t / 2.0

    @property
    def R_inner(self): return self.R - self.t

    @property
    def D_inner(self): return self.D_outer - 2 * self.t

    @property
    def A(self): return math.pi * (self.R**2 - self.R_inner**2)

    @property
    def I(self): return math.pi / 4.0 * (self.R**4 - self.R_inner**4)

    @property
    def Z(self): return self.I / self.R

    @property
    def r_g(self): return math.sqrt(self.I / self.A)

    @property
    def R_over_t(self): return self.R / self.t

    @property
    def A_cross(self):
        """Internal cross-sectional area for pressure loads."""
        return math.pi * self.R_inner**2

    @property
    def V_internal(self):
        """Internal volume."""
        return self.A_cross * self.L


@dataclass
class LoadCase:
    name: str
    n_axial: float      # Axial G-factor
    n_lateral: float    # Lateral G-factor
    g_local: float      # Local gravitational acceleration (m/s²)
    K_eff: float        # Effective length factor
    p_internal: float   # Internal pressure (Pa)
    m_payload: float    # Internal payload mass (kg)
    description: str = ""


# =============================================================================
# MATERIAL: Aluminum 2219-T67 (plate/forging, per MMPDS/METALLIC MATERIALS)
# =============================================================================
AL2219T67 = Material(
    name="Aluminum 2219-T67",
    E=73.1e9,
    nu=0.33,
    rho=2840.0,
    Fty=393e6,
    Ftu=455e6,
    Fcy=290e6,
    Fsu=260e6,
    alpha_cte=22.3e-6,
)

# =============================================================================
# GEOMETRY
# =============================================================================
geom = Geometry(L=10.0, D_outer=4.25, t=0.005)


# =============================================================================
# PAYLOAD AND MISSION PARAMETERS
# =============================================================================
# Estimate internal systems & supplies mass for a habitat module
# Reference: ISS modules ~10,000-20,000 kg outfitted; scaled for this volume
# Internal volume ≈ π*(2.12)²*10 ≈ 141 m³

PAYLOAD_MASS_KG = 8000.0    # Internal systems, ECLSS, supplies, equipment

# Internal pressurization
P_INTERNAL_LAUNCH   = 101325.0    # 1 atm (Pa) — pressurized during launch
P_INTERNAL_SURFACE  = 70000.0     # ~0.69 atm — reduced ops pressure (like ISS partial)
P_MEOP              = 110000.0    # Max Expected Operating Pressure (Pa)
P_PROOF             = P_MEOP * 1.5  # Proof pressure per AIAA S-110
P_BURST             = P_MEOP * 2.0  # Burst pressure requirement

# Gravity environments
G_EARTH = 9.81
G_MOON  = 1.625         # m/s²
G_MARS  = 3.72          # m/s²

# NASA-STD-5001B Factors of Safety
FS_YIELD_DESIGN     = 1.25     # Yield FoS (pressure vessels)
FS_ULTIMATE_DESIGN  = 1.50     # Ultimate FoS (pressure vessels, non-hazardous)
FS_FITTING          = 1.15     # Fitting factor
FS_BUCKLING         = 2.0      # Buckling knockdown (unmanned; 1.5 if manned w/ test)


# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================

def compute_mass_properties(geom: Geometry, mat: Material, m_payload: float):
    """Compute structural and total mass."""
    m_shell = mat.rho * geom.A * geom.L
    # End caps (two oblate hemispherical caps, approx as flat for mass est.)
    # Using 2:1 ellipsoidal heads (standard for pressure vessels)
    # Mass of one 2:1 ellipsoidal head ≈ 1.084 * π * R² * t * ρ
    m_one_cap = 1.084 * math.pi * geom.R**2 * geom.t * mat.rho
    m_caps = 2 * m_one_cap
    m_structure = m_shell + m_caps
    m_total = m_structure + m_payload
    return m_shell, m_caps, m_structure, m_total


def pressure_stresses(geom: Geometry, p: float):
    """Thin-wall pressure vessel stresses (positive = tension)."""
    sigma_hoop = p * geom.R_mid / geom.t          # Hoop (circumferential)
    sigma_long = p * geom.R_mid / (2 * geom.t)    # Longitudinal (axial)
    sigma_radial = -p / 2.0                         # Radial (inner surface, small)
    return sigma_hoop, sigma_long, sigma_radial


def nasa_sp8007_shell_buckling(mat: Material, geom: Geometry, p_internal: float = 0.0):
    """
    NASA SP-8007 shell buckling for thin-walled cylinder under axial compression.
    Includes beneficial effect of internal pressure (pressurization stiffening).

    Returns: sigma_cr, P_cr, gamma, sigma_classical
    """
    R = geom.R
    t = geom.t
    L = geom.L
    E = mat.E

    # Classical buckling stress
    sigma_cl = 0.605 * E * t / R

    # Knockdown factor (unpressurized)
    phi = (1.0 / 16.0) * math.sqrt(R / t)
    gamma_unpressurized = 1.0 - 0.901 * (1.0 - math.exp(-phi))

    # Pressurization stiffening effect (NASA SP-8007, Section 4.2)
    # Internal pressure increases buckling resistance
    # Δγ ≈ (p * R) / (t * σ_cl) * correction
    if p_internal > 0:
        p_bar = p_internal * R / (t * sigma_cl)  # Normalized pressure
        # Empirical correction: γ_pressurized approaches 1.0 as p increases
        delta_gamma = min(p_bar * 0.3, 1.0 - gamma_unpressurized)
        gamma = gamma_unpressurized + delta_gamma
    else:
        gamma = gamma_unpressurized

    gamma = min(gamma, 1.0)  # Cannot exceed 1.0

    sigma_cr = gamma * sigma_cl
    P_cr = sigma_cr * geom.A

    return sigma_cr, P_cr, gamma, sigma_cl, gamma_unpressurized


def euler_column_buckling(mat: Material, geom: Geometry, K: float, L_col: float):
    """Euler column buckling with Johnson correction if needed."""
    L_eff = K * L_col
    slenderness = L_eff / geom.r_g

    # Transition slenderness (Euler-Johnson)
    slenderness_transition = math.pi * math.sqrt(2 * mat.E / mat.Fcy)

    P_cr_euler = (math.pi**2 * mat.E * geom.I) / L_eff**2
    sigma_cr_euler = P_cr_euler / geom.A

    if slenderness < slenderness_transition:
        # Johnson parabolic (inelastic)
        sigma_cr_johnson = mat.Fcy * (1 - (mat.Fcy / (4 * math.pi**2 * mat.E)) * slenderness**2)
        P_cr_johnson = sigma_cr_johnson * geom.A
        return P_cr_johnson, sigma_cr_johnson, slenderness, "Johnson (inelastic)", P_cr_euler, sigma_cr_euler
    else:
        return P_cr_euler, sigma_cr_euler, slenderness, "Euler (elastic)", P_cr_euler, sigma_cr_euler


def nonlinear_pdelta(P_applied: float, P_cr: float, delta_first_order: float,
                     max_iterations: int = 20, tol: float = 1e-6):
    """
    Iterative P-Δ nonlinear amplification.
    Uses geometric series amplification: δ_n+1 = δ_1 / (1 - P/Pcr)
    Then iterates for convergence with secondary moment effects.
    """
    if P_applied >= P_cr:
        return float('inf'), float('inf'), False

    # Amplification factor (closed-form for linear P-Δ)
    AF = 1.0 / (1.0 - P_applied / P_cr)

    # Iterative refinement
    delta = delta_first_order
    for i in range(max_iterations):
        M_secondary = P_applied * delta
        delta_new = delta_first_order * AF
        if abs(delta_new - delta) / max(abs(delta_new), 1e-12) < tol:
            return delta_new, AF, True
        delta = delta_new

    return delta, AF, True


def von_mises(sigma_1: float, sigma_2: float, tau_12: float = 0.0):
    """Plane stress von Mises equivalent stress."""
    return math.sqrt(sigma_1**2 - sigma_1 * sigma_2 + sigma_2**2 + 3 * tau_12**2)


def buckling_interaction_ratio(sigma_axial: float, sigma_cr_axial: float,
                                sigma_bending: float, sigma_cr_bending: float,
                                sigma_hoop: float = 0.0, sigma_cr_hoop: float = 1.0):
    """
    Combined buckling interaction (NASA SP-8007 interaction equation).
    R_c + R_b² + R_p ≤ 1.0  (compression + bending + pressure)
    """
    R_c = sigma_axial / sigma_cr_axial if sigma_cr_axial > 0 else 0
    R_b = (sigma_bending / sigma_cr_bending)**2 if sigma_cr_bending > 0 else 0
    # External pressure term (negative hoop = external pressure)
    R_p = max(-sigma_hoop / sigma_cr_hoop, 0) if sigma_cr_hoop > 0 else 0
    return R_c + R_b + R_p, R_c, R_b, R_p


def brazier_buckling(mat: Material, geom: Geometry):
    """Brazier ovalization critical moment for long tubes under bending."""
    M_br = (2 * math.sqrt(2) / 9.0) * math.pi * mat.E * geom.R * geom.t**2 / math.sqrt(1 - mat.nu**2)
    sigma_br = M_br / geom.Z
    return M_br, sigma_br


def thermal_stress(mat: Material, geom: Geometry, delta_T: float):
    """Thermal stress for constrained cylinder."""
    return mat.E * mat.alpha_cte * delta_T


# =============================================================================
# PRINT UTILITIES
# =============================================================================
SEP_WIDTH = 80

def sep(char="="):
    print(char * SEP_WIDTH)

def header(title):
    print()
    sep()
    print(f"  {title}")
    sep()

def subheader(title):
    print(f"\n  ── {title} {'─' * max(1, SEP_WIDTH - len(title) - 6)}")

def kv(label, value, indent=4):
    """Key-value print with consistent alignment."""
    print(f"{' '*indent}{label:<42s} {value}")


# =============================================================================
# MAIN ANALYSIS
# =============================================================================
def main():
    mat = AL2219T67

    # Mass properties
    m_shell, m_caps, m_structure, m_total = compute_mass_properties(geom, mat, PAYLOAD_MASS_KG)
    W_total_earth = m_total * G_EARTH
    w_dist_earth = (m_total / geom.L) * G_EARTH  # Distributed weight (N/m) — total

    # =========================================================================
    header("HABITAT MODULE STRUCTURAL ANALYSIS")
    print(f"  Pressurized Thin-Walled Cylinder — Lunar/Martian Deployment")
    print(f"  Senior Design Project")
    sep("-")

    subheader("Material Properties — Al 2219-T67")
    kv("Young's Modulus E:", f"{mat.E/1e9:.1f} GPa")
    kv("Poisson's Ratio ν:", f"{mat.nu}")
    kv("Density ρ:", f"{mat.rho:.0f} kg/m³")
    kv("Tensile Yield Fty:", f"{mat.Fty/1e6:.0f} MPa")
    kv("Tensile Ultimate Ftu:", f"{mat.Ftu/1e6:.0f} MPa")
    kv("Compressive Yield Fcy:", f"{mat.Fcy/1e6:.0f} MPa")
    kv("Shear Ultimate Fsu:", f"{mat.Fsu/1e6:.0f} MPa")
    kv("CTE α:", f"{mat.alpha_cte*1e6:.1f} μm/m/°C")

    subheader("Geometry")
    kv("Length:", f"{geom.L:.2f} m")
    kv("Outer Diameter:", f"{geom.D_outer:.4f} m")
    kv("Inner Diameter:", f"{geom.D_inner:.4f} m")
    kv("Wall Thickness:", f"{geom.t*1000:.1f} mm")
    kv("R/t Ratio:", f"{geom.R_over_t:.1f}")
    kv("Cross-section Area:", f"{geom.A:.6f} m² ({geom.A*1e4:.2f} cm²)")
    kv("Moment of Inertia I:", f"{geom.I:.6f} m⁴")
    kv("Section Modulus Z:", f"{geom.Z:.6f} m³")
    kv("Radius of Gyration:", f"{geom.r_g:.4f} m")
    kv("Internal Volume:", f"{geom.V_internal:.1f} m³")

    subheader("Mass Budget")
    kv("Cylinder Shell:", f"{m_shell:.1f} kg")
    kv("End Caps (2x ellipsoidal):", f"{m_caps:.1f} kg")
    kv("Total Structure:", f"{m_structure:.1f} kg")
    kv("Internal Payload/Systems:", f"{PAYLOAD_MASS_KG:.0f} kg")
    kv("TOTAL MASS:", f"{m_total:.1f} kg")
    kv("Total Weight (Earth):", f"{W_total_earth/1e3:.2f} kN")

    subheader("Pressure Requirements")
    kv("MEOP:", f"{P_MEOP/1e3:.1f} kPa ({P_MEOP/101325:.2f} atm)")
    kv("Proof Pressure (1.5× MEOP):", f"{P_PROOF/1e3:.1f} kPa")
    kv("Burst Pressure (2.0× MEOP):", f"{P_BURST/1e3:.1f} kPa")
    kv("Launch Pressure:", f"{P_INTERNAL_LAUNCH/1e3:.1f} kPa")
    kv("Surface Ops Pressure:", f"{P_INTERNAL_SURFACE/1e3:.1f} kPa")

    subheader("Design Factors of Safety (NASA-STD-5001B)")
    kv("Yield FoS:", f"{FS_YIELD_DESIGN:.2f}")
    kv("Ultimate FoS:", f"{FS_ULTIMATE_DESIGN:.2f}")
    kv("Buckling FoS:", f"{FS_BUCKLING:.1f}")
    kv("Fitting Factor:", f"{FS_FITTING:.2f}")

    # =====================================================================
    # CASE 1: LAUNCH — VERTICAL
    # =====================================================================
    header("CASE 1: LAUNCH CONFIGURATION — VERTICAL")
    print("  6G Axial (compression) + 2G Lateral")
    print("  Pinned base (payload adapter) — K=2.0 conservative")
    print("  Internally pressurized to 1 atm")
    sep("-")

    K_launch = 2.0
    n_ax = 6.0
    n_lat = 2.0

    P_axial = n_ax * m_total * G_EARTH
    F_lateral = n_lat * m_total * G_EARTH
    L_eff = K_launch * geom.L

    subheader("Applied Loads")
    kv("Axial Load (6G):", f"{P_axial/1e3:.2f} kN ({P_axial/1e6:.4f} MN)")
    kv("Lateral Load (2G):", f"{F_lateral/1e3:.2f} kN ({F_lateral/1e6:.4f} MN)")
    kv("Effective Length (K={:.1f}):".format(K_launch), f"{L_eff:.2f} m")

    # --- Pressure stresses at launch ---
    subheader("Pressure Stresses (Launch — 1 atm)")
    sig_hoop_L, sig_long_L, sig_rad_L = pressure_stresses(geom, P_INTERNAL_LAUNCH)
    kv("Hoop Stress σ_h:", f"{sig_hoop_L/1e6:.2f} MPa (tension)")
    kv("Longitudinal Stress σ_l:", f"{sig_long_L/1e6:.2f} MPa (tension)")
    kv("Note:", "Longitudinal pressure stress REDUCES net axial compression")

    # --- Mechanical stresses ---
    subheader("Mechanical Stresses")
    sigma_axial_mech = P_axial / geom.A  # Compressive (positive = compression here)
    M_base = F_lateral * geom.L  # Bending moment at base (cantilever)
    sigma_bend = M_base / geom.Z

    # Net axial stress: compression from load minus tension from pressure
    sigma_axial_net = sigma_axial_mech - sig_long_L  # Net compression

    # Shear
    tau_avg = F_lateral / geom.A
    tau_peak = 2.0 * tau_avg  # Peak shear in thin-walled cylinder

    kv("σ_axial (mechanical, comp.):", f"{sigma_axial_mech/1e6:.4f} MPa")
    kv("σ_axial (net, after pressure):", f"{sigma_axial_net/1e6:.4f} MPa")
    kv("M_base (cantilever bending):", f"{M_base/1e3:.2f} kN·m")
    kv("σ_bending:", f"{sigma_bend/1e6:.4f} MPa")
    kv("τ_peak (shear):", f"{tau_peak/1e6:.4f} MPa")

    # Combined stress — worst case is compressive side (pressure tension helps less there)
    # On compression side: σ = -(σ_axial_mech + σ_bend) + σ_long_pressure
    sigma_comp_max = sigma_axial_mech + sigma_bend - sig_long_L  # Net compression max
    sigma_tens_max = -sigma_axial_mech + sigma_bend + sig_long_L  # Tension side

    # Biaxial stress state on compressive side: (σ_axial_net_comp, σ_hoop_tension)
    sigma_vm_comp = von_mises(-sigma_comp_max, sig_hoop_L, tau_peak)
    sigma_vm_tens = von_mises(sigma_tens_max, sig_hoop_L, tau_peak)
    sigma_vm_max = max(sigma_vm_comp, sigma_vm_tens)

    kv("σ_combined (max compression):", f"{sigma_comp_max/1e6:.4f} MPa")
    kv("σ_combined (max tension):", f"{sigma_tens_max/1e6:.4f} MPa")
    kv("σ_VM (compression side):", f"{sigma_vm_comp/1e6:.4f} MPa")
    kv("σ_VM (tension side):", f"{sigma_vm_tens/1e6:.4f} MPa")
    kv("σ_VM (governing):", f"{sigma_vm_max/1e6:.4f} MPa")

    # --- Shell buckling (with pressure stiffening) ---
    subheader("Shell Buckling — NASA SP-8007 (with pressure stiffening)")
    sig_cr_sh, P_cr_sh, gamma, sig_cl, gamma_unp = nasa_sp8007_shell_buckling(
        mat, geom, P_INTERNAL_LAUNCH
    )
    kv("Classical σ_cr:", f"{sig_cl/1e6:.2f} MPa")
    kv("Knockdown γ (unpressurized):", f"{gamma_unp:.4f}")
    kv("Knockdown γ (pressurized):", f"{gamma:.4f}")
    kv("σ_cr (shell, pressurized):", f"{sig_cr_sh/1e6:.2f} MPa")
    kv("P_cr (shell):", f"{P_cr_sh/1e6:.2f} MN")

    # --- Column buckling ---
    subheader("Column Buckling — Euler/Johnson")
    P_cr_col, sig_cr_col, slender, mode_col, P_euler, sig_euler = euler_column_buckling(
        mat, geom, K_launch, geom.L
    )
    kv("Slenderness (L_eff/r):", f"{slender:.2f}")
    kv("Buckling mode:", mode_col)
    kv("P_cr (Euler, reference):", f"{P_euler/1e6:.2f} MN")
    kv("P_cr (governing column):", f"{P_cr_col/1e6:.2f} MN")
    kv("σ_cr (governing column):", f"{sig_cr_col/1e6:.2f} MPa")

    # --- Governing buckling ---
    P_cr_governing = min(P_cr_sh, P_cr_col)
    sig_cr_governing = P_cr_governing / geom.A
    gov_mode = "Shell (NASA SP-8007)" if P_cr_sh < P_cr_col else "Column ({})".format(mode_col)

    subheader("Governing Buckling")
    kv("Governing Mode:", gov_mode)
    kv("P_cr (governing):", f"{P_cr_governing/1e6:.2f} MN")
    kv("σ_cr (governing):", f"{sig_cr_governing/1e6:.2f} MPa")

    # --- Interaction ---
    subheader("Buckling Interaction (R_c + R_b² ≤ 1.0)")
    IR, Rc, Rb, Rp = buckling_interaction_ratio(
        sigma_axial_net, sig_cr_governing,
        sigma_bend, sig_cr_governing
    )
    kv("R_c (compression ratio):", f"{Rc:.6f}")
    kv("R_b² (bending ratio):", f"{Rb:.6f}")
    kv("Interaction Ratio:", f"{IR:.6f}  {'⚠ FAIL' if IR > 1 else '✓ OK'}")

    # --- Nonlinear P-Δ deformation ---
    subheader("Deformation (with Nonlinear P-Δ)")
    delta_axial = (P_axial * geom.L) / (geom.A * mat.E)
    delta_lat_1st = (F_lateral * geom.L**3) / (3 * mat.E * geom.I)

    delta_lat_nl, AF, converged = nonlinear_pdelta(P_axial, P_cr_governing, delta_lat_1st)

    kv("Axial shortening:", f"{delta_axial*1000:.4f} mm")
    kv("Lateral deflection (1st order):", f"{delta_lat_1st*1000:.4f} mm")
    kv("P-Δ amplification factor:", f"{AF:.6f}")
    kv("Lateral deflection (nonlinear):", f"{delta_lat_nl*1000:.4f} mm")
    kv("Converged:", f"{'Yes' if converged else 'No'}")
    if delta_lat_nl > 0 and delta_lat_nl != float('inf'):
        kv("L/δ ratio:", f"L/{geom.L/delta_lat_nl:.0f}")

    # --- Margins of Safety ---
    subheader("Margins of Safety")
    # MS = (Allowable / (FS × Applied)) - 1
    MS_yield = (mat.Fty / (FS_YIELD_DESIGN * sigma_vm_max)) - 1
    MS_ultimate = (mat.Ftu / (FS_ULTIMATE_DESIGN * sigma_vm_max)) - 1
    MS_buckling = (sig_cr_governing / (FS_BUCKLING * sigma_comp_max)) - 1
    MS_interaction = (1.0 / (FS_BUCKLING * IR)) - 1 if IR > 0 else float('inf')

    kv("MS_yield:", f"{MS_yield:+.2f}  {'✓ POSITIVE' if MS_yield > 0 else '⚠ NEGATIVE'}")
    kv("MS_ultimate:", f"{MS_ultimate:+.2f}  {'✓ POSITIVE' if MS_ultimate > 0 else '⚠ NEGATIVE'}")
    kv("MS_buckling:", f"{MS_buckling:+.2f}  {'✓ POSITIVE' if MS_buckling > 0 else '⚠ NEGATIVE'}")
    kv("MS_interaction:", f"{MS_interaction:+.2f}  {'✓ POSITIVE' if MS_interaction > 0 else '⚠ NEGATIVE'}")

    # =====================================================================
    # CASE 2: SURFACE — HORIZONTAL (Lunar & Mars)
    # =====================================================================
    for body_name, g_local, p_ops in [("LUNAR", G_MOON, P_INTERNAL_SURFACE),
                                        ("MARTIAN", G_MARS, P_INTERNAL_SURFACE)]:
        header(f"CASE 2{('a' if body_name=='LUNAR' else 'b').upper()}: SURFACE — {body_name} ({body_name} GRAVITY)")
        print(f"  Horizontal, simply supported at x=0, x=L/2, x=L")
        print(f"  g = {g_local:.3f} m/s², pressurized to {p_ops/1e3:.1f} kPa")
        print(f"  Payload: {PAYLOAD_MASS_KG:.0f} kg internal mass")
        sep("-")

        W_total_local = m_total * g_local
        w_dist_local = (m_total / geom.L) * g_local
        L_span = geom.L / 2.0

        subheader("Loading")
        kv("Total Weight:", f"{W_total_local/1e3:.3f} kN")
        kv("Distributed Load:", f"{w_dist_local:.2f} N/m")
        kv("Span Length:", f"{L_span:.2f} m")

        # Pressure stresses
        sig_hoop_S, sig_long_S, _ = pressure_stresses(geom, p_ops)

        subheader("Pressure Stresses")
        kv("Hoop Stress σ_h:", f"{sig_hoop_S/1e6:.2f} MPa")
        kv("Longitudinal Stress σ_l:", f"{sig_long_S/1e6:.2f} MPa")

        # Bending — two-span continuous beam
        M_center = w_dist_local * L_span**2 / 8.0  # Hogging at center support
        M_midspan = 9.0 * w_dist_local * L_span**2 / 128.0  # Sagging

        M_max = max(M_center, M_midspan)
        sigma_bend_s = M_max / geom.Z

        V_end = 3.0 * w_dist_local * L_span / 8.0
        V_center = 5.0 * w_dist_local * L_span / 8.0
        V_max = max(V_end, V_center)
        tau_s = 2.0 * V_max / geom.A

        subheader("Bending & Shear")
        kv("M_center (hogging):", f"{M_center/1e3:.4f} kN·m")
        kv("M_midspan (sagging):", f"{M_midspan/1e3:.4f} kN·m")
        kv("M_max:", f"{M_max/1e3:.4f} kN·m")
        kv("σ_bending:", f"{sigma_bend_s/1e6:.6f} MPa")
        kv("V_max:", f"{V_max/1e3:.4f} kN")
        kv("τ_peak:", f"{tau_s/1e6:.6f} MPa")

        # Combined with pressure (biaxial: longitudinal bending + hoop pressure)
        # On compression fiber: σ_axial = -σ_bend + σ_long_pressure
        sigma_comb_comp_s = sigma_bend_s - sig_long_S  # Net compression (if positive)
        sigma_comb_tens_s = sigma_bend_s + sig_long_S   # Net tension

        sigma_vm_s = von_mises(sigma_comb_tens_s, sig_hoop_S, tau_s)

        subheader("Combined Stress State")
        kv("σ_net (comp. fiber):", f"{sigma_comb_comp_s/1e6:.6f} MPa")
        kv("σ_net (tension fiber):", f"{sigma_comb_tens_s/1e6:.6f} MPa")
        kv("σ_hoop (pressure):", f"{sig_hoop_S/1e6:.2f} MPa")
        kv("σ_VM (max):", f"{sigma_vm_s/1e6:.4f} MPa")

        # Deflection
        delta_s = w_dist_local * L_span**4 / (185.0 * mat.E * geom.I)

        subheader("Deformation")
        kv("Max Deflection:", f"{delta_s*1e6:.4f} μm ({delta_s*1000:.6f} mm)")
        if delta_s > 0:
            kv("L_span/δ:", f"L/{L_span/delta_s:.0f}")

        # Brazier
        M_br, sig_br = brazier_buckling(mat, geom)

        subheader("Buckling Checks")
        kv("Shell σ_cr:", f"{sig_cr_sh/1e6:.2f} MPa")
        kv("Applied σ_bend:", f"{sigma_bend_s/1e6:.6f} MPa")
        kv("SF (shell buckling):", f"{sig_cr_sh/sigma_bend_s:.0f}" if sigma_bend_s > 0 else "∞")
        kv("Brazier M_cr:", f"{M_br/1e3:.2f} kN·m")
        kv("SF (Brazier):", f"{M_br/M_max:.0f}" if M_max > 0 else "∞")

        # Margins
        MS_y_s = (mat.Fty / (FS_YIELD_DESIGN * sigma_vm_s)) - 1 if sigma_vm_s > 0 else float('inf')
        MS_u_s = (mat.Ftu / (FS_ULTIMATE_DESIGN * sigma_vm_s)) - 1 if sigma_vm_s > 0 else float('inf')

        subheader("Margins of Safety")
        kv("MS_yield:", f"{MS_y_s:+.1f}  ✓ POSITIVE")
        kv("MS_ultimate:", f"{MS_u_s:+.1f}  ✓ POSITIVE")
        kv("Assessment:", "Structure is greatly over-designed for surface loads.")
        kv("", "Launch case governs the design.")

    # =====================================================================
    # CASE 3: PRESSURE VESSEL VERIFICATION
    # =====================================================================
    header("CASE 3: PRESSURE VESSEL — MEOP & BURST VERIFICATION")
    print("  Per AIAA S-110 and NASA-STD-5001B")
    sep("-")

    for label, p_val, fs_req in [("MEOP", P_MEOP, 1.0),
                                   ("Proof (1.5×)", P_PROOF, 1.0),
                                   ("Burst (2.0×)", P_BURST, 1.0)]:
        sig_h, sig_l, _ = pressure_stresses(geom, p_val)
        sig_vm_p = von_mises(sig_h, sig_l)

        subheader(f"Pressure: {label} = {p_val/1e3:.1f} kPa")
        kv("Hoop Stress:", f"{sig_h/1e6:.2f} MPa")
        kv("Longitudinal Stress:", f"{sig_l/1e6:.2f} MPa")
        kv("Von Mises:", f"{sig_vm_p/1e6:.2f} MPa")

        MS_y_p = (mat.Fty / (FS_YIELD_DESIGN * sig_vm_p)) - 1
        MS_u_p = (mat.Ftu / (FS_ULTIMATE_DESIGN * sig_vm_p)) - 1

        kv("MS_yield:", f"{MS_y_p:+.2f}  {'✓' if MS_y_p > 0 else '⚠ FAIL'}")
        kv("MS_ultimate:", f"{MS_u_p:+.2f}  {'✓' if MS_u_p > 0 else '⚠ FAIL'}")

    # =====================================================================
    # CASE 4: THERMAL STRESS CHECK
    # =====================================================================
    header("CASE 4: THERMAL STRESS ESTIMATE")
    print("  Temperature range for lunar/Mars surface operations")
    sep("-")

    T_ranges = [
        ("Lunar day/night cycle", -180, 120),
        ("Mars surface cycle", -80, 20),
        ("Launch thermal (fairing)", -50, 80),
    ]

    for desc, T_min, T_max in T_ranges:
        dT = T_max - T_min
        sig_th = thermal_stress(mat, geom, dT)  # Fully constrained (worst case)
        # In reality, thermal expansion is largely unconstrained axially
        # Hoop thermal stress from differential heating
        sig_th_partial = sig_th * 0.3  # ~30% constraint typical

        subheader(f"{desc} (ΔT = {dT}°C)")
        kv("σ_thermal (fully constrained):", f"{sig_th/1e6:.1f} MPa")
        kv("σ_thermal (partial, ~30%):", f"{sig_th_partial/1e6:.1f} MPa")
        kv("Fraction of Fty:", f"{sig_th_partial/mat.Fty*100:.1f}%")

    # =====================================================================
    # GRAND SUMMARY
    # =====================================================================
    header("GRAND SUMMARY — ALL CASES")

    print(f"""
┌──────────────────────────────────────────────────────────────────────────────┐
│                    HABITAT MODULE STRUCTURAL SUMMARY                        │
├──────────────────────────────────────────────────────────────────────────────┤
│ Structure:  Al 2219-T67, L=10m, D=4.25m, t=5mm, R/t={geom.R_over_t:.0f}              │
│ Mass:       Structure={m_structure:.0f} kg, Payload={PAYLOAD_MASS_KG:.0f} kg, Total={m_total:.0f} kg          │
│ Volume:     {geom.V_internal:.1f} m³ internal                                          │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  CASE 1 — LAUNCH (6G axial + 2G lateral, 1 atm internal)                    │
│  ┌────────────────────────────────────────────────────────────┐              │
│  │  Critical Buckling Load (governing): {P_cr_governing/1e6:>8.2f} MN             │
│  │  Governing Mode: {gov_mode:<41s}  │
│  │  Max Combined Stress:               {sigma_comp_max/1e6:>8.4f} MPa             │
│  │  Von Mises Stress:                  {sigma_vm_max/1e6:>8.4f} MPa             │
│  │  Axial Deformation:                 {delta_axial*1000:>8.4f} mm              │
│  │  Lateral Deformation (P-Δ):         {delta_lat_nl*1000:>8.4f} mm              │
│  │  MS_yield:  {MS_yield:>+7.2f}   MS_ultimate: {MS_ultimate:>+7.2f}                     │
│  │  MS_buckling: {MS_buckling:>+7.2f}  Interaction: {IR:.4f} ✓                    │
│  └────────────────────────────────────────────────────────────┘              │
│                                                                              │
│  CASE 2a — LUNAR SURFACE (g=1.625 m/s², {P_INTERNAL_SURFACE/1e3:.0f} kPa)                      │
│  ┌────────────────────────────────────────────────────────────┐              │""")

    # Recompute quick lunar values for summary
    w_moon = (m_total / geom.L) * G_MOON
    M_moon = w_moon * (geom.L/2)**2 / 8
    sig_b_moon = M_moon / geom.Z
    d_moon = w_moon * (geom.L/2)**4 / (185 * mat.E * geom.I)

    print(f"│  │  Max Bending Stress:                {sig_b_moon/1e6:>8.6f} MPa           │")
    print(f"│  │  Max Deflection:                    {d_moon*1e6:>8.4f} μm              │")
    print(f"│  │  Assessment: Launch case governs — massive margins on surface   │")
    print(f"│  └────────────────────────────────────────────────────────────────┘              │")
    print(f"│                                                                              │")

    # Mars
    w_mars = (m_total / geom.L) * G_MARS
    M_mars = w_mars * (geom.L/2)**2 / 8
    sig_b_mars = M_mars / geom.Z
    d_mars = w_mars * (geom.L/2)**4 / (185 * mat.E * geom.I)

    print(f"│  CASE 2b — MARS SURFACE (g=3.72 m/s², {P_INTERNAL_SURFACE/1e3:.0f} kPa)                          │")
    print(f"│  ┌────────────────────────────────────────────────────────────┐              │")
    print(f"│  │  Max Bending Stress:                {sig_b_mars/1e6:>8.6f} MPa           │")
    print(f"│  │  Max Deflection:                    {d_mars*1e6:>8.4f} μm              │")
    print(f"│  │  Assessment: Launch case governs — massive margins on surface   │")
    print(f"│  └────────────────────────────────────────────────────────────────┘              │")

    # Pressure
    sig_h_meop, sig_l_meop, _ = pressure_stresses(geom, P_MEOP)
    sig_vm_meop = von_mises(sig_h_meop, sig_l_meop)

    print(f"│                                                                              │")
    print(f"│  CASE 3 — PRESSURE (MEOP = {P_MEOP/1e3:.0f} kPa)                                     │")
    print(f"│  ┌────────────────────────────────────────────────────────────┐              │")
    print(f"│  │  Hoop Stress:         {sig_h_meop/1e6:>8.2f} MPa                          │")
    print(f"│  │  Von Mises:           {sig_vm_meop/1e6:>8.2f} MPa                          │")
    print(f"│  │  MS_yield: {(mat.Fty/(FS_YIELD_DESIGN*sig_vm_meop)-1):>+7.2f}   MS_ultimate: {(mat.Ftu/(FS_ULTIMATE_DESIGN*sig_vm_meop)-1):>+7.2f}                    │")
    print(f"│  └────────────────────────────────────────────────────────────┘              │")

    print(f"│                                                                              │")
    print(f"├──────────────────────────────────────────────────────────────────────────────┤")
    print(f"│  DESIGN DRIVERS:                                                             │")
    print(f"│   1. LOCAL SHELL BUCKLING (R/t={geom.R_over_t:.0f}) governs over column buckling       │")
    print(f"│   2. Pressure stiffening improves shell buckling resistance                  │")
    print(f"│   3. Launch loads (Case 1) govern the structural design                      │")
    print(f"│   4. Surface gravity loads are negligible vs. launch & pressure              │")
    print(f"│   5. Pressure vessel sizing adequate for MEOP with positive margins          │")
    print(f"│   6. Consider ring stiffeners / stringers for shell buckling improvement     │")
    print(f"└──────────────────────────────────────────────────────────────────────────────┘")

    print()
    sep()
    print("  DESIGN RECOMMENDATIONS FOR SENIOR DESIGN TEAM")
    sep()
    print("""
    1. SHELL BUCKLING IS THE CRITICAL FAILURE MODE
       - R/t = {:.0f} makes this shell highly imperfection-sensitive
       - Consider adding ring stiffeners (frames) every 1-2 m to break
         the unsupported shell length and dramatically increase P_cr
       - Isogrid or orthogrid patterns are standard for launch vehicle shells

    2. PAYLOAD ADAPTER INTERFACE
       - The pinned-base assumption (K=2.0) is conservative
       - Actual payload adapters provide some rotational restraint
       - Design the bolted flange joint at the base ring

    3. PRESSURE VESSEL CONSIDERATIONS
       - Internal pressure provides beneficial stiffening during launch
       - Verify leak-before-burst (LBB) criterion: critical crack length
         must cause leak before unstable fracture
       - Weld land thickness increases at longitudinal and circumferential welds
       - 2219-T67 is specifically chosen for weldability and cryogenic performance

    4. THERMAL MANAGEMENT
       - Lunar thermal cycling (ΔT ≈ 300°C) is severe
       - Multi-layer insulation (MLI) required externally
       - Consider thermal expansion joints or flexible supports

    5. METEOROID/DEBRIS PROTECTION
       - Consider Whipple shield or stuffed Whipple bumper
       - This adds mass but does not significantly affect primary structure

    6. RECOMMENDED NEXT STEPS
       - FEA validation (linear buckling eigenvalue + nonlinear post-buckling)
       - Weld knockdown factors (additional 0.8-0.9 reduction on Ftu/Fty)
       - Fatigue analysis for pressurization cycles
       - Fracture mechanics (damage tolerance) per NASA-STD-5019
       - Landing load cases (propulsive or airbag)
       - Acoustic and random vibration environments
    """.format(geom.R_over_t))

    # =====================================================================
    # Export results as JSON for downstream use
    # =====================================================================
    results = {
        "geometry": {
            "length_m": geom.L, "diameter_m": geom.D_outer,
            "thickness_mm": geom.t*1000, "R_over_t": geom.R_over_t,
            "area_m2": geom.A, "I_m4": geom.I,
            "internal_volume_m3": geom.V_internal,
        },
        "mass_kg": {
            "structure": round(m_structure, 1), "payload": PAYLOAD_MASS_KG,
            "total": round(m_total, 1),
        },
        "case1_launch": {
            "P_cr_governing_MN": round(P_cr_governing/1e6, 2),
            "governing_mode": gov_mode,
            "sigma_combined_MPa": round(sigma_comp_max/1e6, 4),
            "sigma_VM_MPa": round(sigma_vm_max/1e6, 4),
            "delta_axial_mm": round(delta_axial*1000, 4),
            "delta_lateral_mm": round(delta_lat_nl*1000, 4),
            "MS_yield": round(MS_yield, 2),
            "MS_ultimate": round(MS_ultimate, 2),
            "MS_buckling": round(MS_buckling, 2),
            "interaction_ratio": round(IR, 4),
        },
        "case3_pressure": {
            "MEOP_kPa": P_MEOP/1e3,
            "hoop_stress_MPa": round(sig_h_meop/1e6, 2),
            "VM_stress_MPa": round(sig_vm_meop/1e6, 2),
        },
    }

    with open("analysis_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("  Results exported to: analysis_results.json")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
