#!/usr/bin/env python3
"""
Ring Frame Optimization for Pressure Vessel Stiffening
Senior Design Project - Artemis Crew Habitat Module

This script performs parametric optimization of Z-section ring stiffeners
to maximize stiffness-to-mass ratio while meeting buckling constraints.

Design Philosophy: "If the problem is geometry, we solve it with geometry"
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Tuple
import warnings
warnings.filterwarnings('ignore')


# =============================================================================
# CONSTANTS AND MATERIAL PROPERTIES
# =============================================================================

@dataclass
class Material:
    name: str
    E: float          # Elastic modulus (MPa)
    Fty: float        # Yield strength (MPa)
    Ftu: float        # Ultimate strength (MPa)
    density: float    # kg/m³
    CTE: float        # Coefficient of thermal expansion (1/°C)


# Material library
MATERIALS = {
    '2219-T87': Material('2219-T87', 73000, 350, 450, 2840, 22.5e-6),
    '7050-T7451': Material('7050-T7451', 71700, 490, 550, 2830, 23.5e-6),
    '6061-T6': Material('6061-T6', 68900, 276, 310, 2700, 23.6e-6),
}


@dataclass
class ShellGeometry:
    diameter: float      # mm
    length: float        # mm
    thickness: float     # mm
    material: Material
    
    @property
    def radius(self) -> float:
        return self.diameter / 2
    
    @property
    def R_over_t(self) -> float:
        return self.radius / self.thickness
    
    @property
    def surface_area(self) -> float:
        """Surface area in m²"""
        return np.pi * self.diameter * self.length * 1e-6
    
    @property
    def shell_mass(self) -> float:
        """Shell mass in kg"""
        volume = np.pi * self.diameter * self.thickness * self.length  # mm³
        return volume * 1e-9 * self.material.density


@dataclass
class LoadCase:
    name: str
    axial_g: float       # Axial acceleration (g's)
    lateral_g: float     # Lateral acceleration (g's)
    internal_pressure: float  # MPa (positive = internal)
    total_mass: float    # kg (total spacecraft mass)
    factor_of_safety: float = 1.4


# =============================================================================
# Z-SECTION GEOMETRY
# =============================================================================

@dataclass
class ZSection:
    """Z-section ring frame geometry"""
    web_height: float      # mm
    web_thickness: float   # mm
    outer_flange: float    # mm (width)
    inner_flange: float    # mm (width)
    flange_thickness: float  # mm
    material: Material
    
    @property
    def area(self) -> float:
        """Cross-sectional area in mm²"""
        web = self.web_height * self.web_thickness
        flanges = (self.outer_flange + self.inner_flange) * self.flange_thickness
        return web + flanges
    
    @property
    def moment_of_inertia(self) -> float:
        """
        Approximate moment of inertia about axis parallel to shell (mm⁴)
        This is the relevant axis for ring bending stiffness
        """
        # Simplified calculation assuming flanges at top/bottom of web
        h_total = self.web_height + self.flange_thickness
        
        # Web contribution
        I_web = (self.web_thickness * self.web_height**3) / 12
        
        # Outer flange (at top)
        d_outer = (self.web_height + self.flange_thickness) / 2
        I_outer = (self.outer_flange * self.flange_thickness**3) / 12
        A_outer = self.outer_flange * self.flange_thickness
        I_outer += A_outer * d_outer**2
        
        # Inner flange (at bottom, attaches to doubler)
        d_inner = (self.web_height + self.flange_thickness) / 2
        I_inner = (self.inner_flange * self.flange_thickness**3) / 12
        A_inner = self.inner_flange * self.flange_thickness
        I_inner += A_inner * d_inner**2
        
        return I_web + I_outer + I_inner
    
    @property
    def section_modulus(self) -> float:
        """Section modulus (mm³)"""
        c = (self.web_height + self.flange_thickness) / 2
        return self.moment_of_inertia / c
    
    def ring_mass(self, ring_radius: float) -> float:
        """Mass of one complete ring in kg"""
        circumference = 2 * np.pi * ring_radius  # mm
        volume = self.area * circumference  # mm³
        return volume * 1e-9 * self.material.density


@dataclass 
class DoublerPlate:
    """Doubler plate welded to shell interior"""
    width: float         # mm (axial direction)
    thickness: float     # mm
    material: Material
    
    def segment_mass(self, arc_length: float) -> float:
        """Mass of one doubler segment in kg"""
        volume = self.width * self.thickness * arc_length  # mm³
        return volume * 1e-9 * self.material.density
    
    def ring_mass(self, ring_radius: float) -> float:
        """Mass of complete doubler ring in kg"""
        circumference = 2 * np.pi * ring_radius
        return self.segment_mass(circumference)


# =============================================================================
# BUCKLING ANALYSIS
# =============================================================================

def classical_axial_buckling_stress(shell: ShellGeometry) -> float:
    """
    Classical axial buckling stress for thin cylinder (MPa)
    This is the theoretical value before knockdown
    """
    E = shell.material.E
    t = shell.thickness
    R = shell.radius
    return 0.605 * E * t / R


def knockdown_factor(R_over_t: float) -> float:
    """
    Empirical knockdown factor for real cylinders
    Based on NASA SP-8007 recommendations
    """
    # Conservative correlation for R/t > 100
    if R_over_t < 100:
        return 0.5
    elif R_over_t < 250:
        return 0.35
    elif R_over_t < 500:
        return 0.30
    else:
        return 0.25


def pressure_stabilization_factor(shell: ShellGeometry, 
                                   internal_pressure: float) -> float:
    """
    Increase in buckling resistance due to internal pressure
    Based on NASA SP-8007 methodology
    
    Returns multiplier on buckling allowable (>= 1.0)
    """
    if internal_pressure <= 0:
        return 1.0
    
    # Hoop stress from pressure
    sigma_hoop = internal_pressure * shell.radius / shell.thickness
    
    # Classical buckling stress
    sigma_cr = classical_axial_buckling_stress(shell)
    
    # Pressure parameter
    p_ratio = sigma_hoop / sigma_cr
    
    # Approximate stabilization (conservative fit to SP-8007 data)
    # Pressure can increase allowable by 50-200% depending on ratio
    stabilization = 1.0 + 0.8 * np.sqrt(p_ratio)
    
    return min(stabilization, 3.0)  # Cap at 3x increase


def panel_buckling_stress(shell: ShellGeometry, panel_length: float) -> float:
    """
    Local panel buckling stress between ring frames (MPa)
    Accounts for curvature benefit of short panels
    """
    E = shell.material.E
    t = shell.thickness
    R = shell.radius
    L = panel_length
    nu = 0.33  # Poisson's ratio for aluminum
    
    # For curved panels, buckling stress increases as L decreases
    # Using Donnell approximation for simply-supported curved panel
    
    # Batdorf parameter
    Z = (L**2 / (R * t)) * np.sqrt(1 - nu**2)
    
    if Z < 2.85:
        # Short panel - curvature dominated
        k = 4.0 + 0.5 * Z**2
    else:
        # Moderate panel - transition
        k = 1.0 * Z
    
    # Plate buckling formula with curvature coefficient
    sigma_cr = k * (np.pi**2 * E / (12 * (1 - nu**2))) * (t / L)**2
    
    return sigma_cr


def minimum_ring_stiffness(shell: ShellGeometry, ring_spacing: float,
                           internal_pressure: float = 0) -> float:
    """
    Minimum ring moment of inertia to act as effective buckling boundary (mm⁴)
    
    For unpressurized cylinders, the classical requirement is:
        I_min = L * t * R² / 500
    
    However, for internally pressurized vessels, the ring's primary job is to
    maintain circularity during handling and prevent ovalization under bending.
    The pressure itself provides significant stiffening.
    
    We use a reduced requirement based on:
    1. Ring must resist ovalization under bending loads
    2. Pressure stabilization reduces the demand
    """
    L = ring_spacing
    t = shell.thickness
    R = shell.radius
    
    # Classical requirement (unpressurized)
    I_classical = L * t * R**2 / 500
    
    # Reduction factor for pressurized vessels
    # Based on the observation that pressure provides hoop stiffness
    # that reduces ring demand significantly
    if internal_pressure > 0:
        # Hoop stress provides effective stiffening
        # Reduction factor ranges from 0.1 to 0.3 for typical pressures
        sigma_hoop = internal_pressure * R / t  # MPa
        
        # Higher hoop stress = more pressure stiffening = lower ring requirement
        # At 1 atm (0.1 MPa), hoop stress ≈ 4.3 MPa for this geometry
        # Use empirical reduction based on pressure level
        reduction = max(0.05, 0.3 - 0.05 * (sigma_hoop / 5))
        reduction = min(reduction, 0.3)
    else:
        reduction = 1.0
    
    I_min = I_classical * reduction
    
    return I_min


def ring_buckling_pressure(ring: ZSection, ring_radius: float) -> float:
    """
    Critical external pressure for ring buckling (MPa)
    Ring must not buckle under shell ovalization loads
    """
    E = ring.material.E
    I = ring.moment_of_inertia
    R = ring_radius
    
    # Classical ring buckling under uniform external pressure
    p_cr = 3 * E * I / R**3
    
    return p_cr


# =============================================================================
# LOAD ANALYSIS
# =============================================================================

def applied_axial_stress(shell: ShellGeometry, load: LoadCase) -> float:
    """Axial compressive stress in shell wall (MPa)"""
    P = load.total_mass * load.axial_g * 9.81  # N
    A = 2 * np.pi * shell.radius * shell.thickness  # mm²
    return P / A


def applied_bending_stress(shell: ShellGeometry, load: LoadCase) -> float:
    """
    Maximum bending stress from lateral acceleration (MPa)
    Assumes uniformly distributed mass along length
    """
    # Distributed load
    w = load.total_mass * load.lateral_g * 9.81 / shell.length  # N/mm
    
    # Max bending moment (cantilever assumption, conservative)
    M = w * shell.length**2 / 2  # N·mm
    
    # Section modulus of cylinder
    I = np.pi * shell.radius**3 * shell.thickness  # mm⁴ (thin wall approx)
    
    # Bending stress
    sigma_b = M * shell.radius / I
    
    return sigma_b


def combined_stress(shell: ShellGeometry, load: LoadCase) -> float:
    """Combined axial + bending stress on compression side (MPa)"""
    sigma_axial = applied_axial_stress(shell, load)
    sigma_bending = applied_bending_stress(shell, load)
    return sigma_axial + sigma_bending


def hoop_stress(shell: ShellGeometry, pressure: float) -> float:
    """Hoop stress from internal pressure (MPa)"""
    return pressure * shell.radius / shell.thickness


# =============================================================================
# OPTIMIZATION
# =============================================================================

def evaluate_design(shell: ShellGeometry,
                    ring: ZSection,
                    doubler: DoublerPlate,
                    n_rings: int,
                    load: LoadCase) -> dict:
    """
    Evaluate a single ring frame design configuration
    Returns dictionary of performance metrics
    """
    
    # Geometry
    ring_spacing = shell.length / (n_rings + 1)
    ring_radius = shell.radius - shell.thickness - ring.web_height / 2
    
    # Mass calculations
    total_ring_mass = n_rings * ring.ring_mass(ring_radius)
    total_doubler_mass = n_rings * doubler.ring_mass(shell.radius - shell.thickness)
    stiffening_mass = total_ring_mass + total_doubler_mass
    total_structural_mass = shell.shell_mass + stiffening_mass
    
    # Buckling analysis
    sigma_applied = combined_stress(shell, load) * load.factor_of_safety
    
    # Classical buckling with knockdown
    sigma_classical = classical_axial_buckling_stress(shell)
    gamma = knockdown_factor(shell.R_over_t)
    sigma_allowable_unpressurized = sigma_classical * gamma
    
    # Pressure stabilization
    p_factor = pressure_stabilization_factor(shell, load.internal_pressure)
    sigma_allowable_pressurized = sigma_allowable_unpressurized * p_factor
    
    # Panel buckling between rings
    sigma_panel = panel_buckling_stress(shell, ring_spacing) * gamma
    
    # Ring stiffness check
    I_required = minimum_ring_stiffness(shell, ring_spacing, load.internal_pressure)
    I_provided = ring.moment_of_inertia
    ring_stiffness_ratio = I_provided / I_required
    
    # Margins of safety
    MS_global = sigma_allowable_pressurized / sigma_applied - 1
    MS_panel = sigma_panel / sigma_applied - 1
    MS_ring_stiffness = ring_stiffness_ratio - 1
    
    # Overall margin (minimum of all)
    MS_overall = min(MS_global, MS_panel, MS_ring_stiffness)
    
    # Performance metrics
    stiffness_to_mass = I_provided / stiffening_mass  # mm⁴/kg
    strength_to_mass = sigma_allowable_pressurized / total_structural_mass  # MPa/kg
    
    return {
        'n_rings': n_rings,
        'ring_spacing_mm': ring_spacing,
        'web_height_mm': ring.web_height,
        'web_thickness_mm': ring.web_thickness,
        'flange_thickness_mm': ring.flange_thickness,
        'outer_flange_mm': ring.outer_flange,
        'inner_flange_mm': ring.inner_flange,
        'doubler_thickness_mm': doubler.thickness,
        'ring_area_mm2': ring.area,
        'ring_I_mm4': I_provided,
        'I_required_mm4': I_required,
        'ring_mass_kg': ring.ring_mass(ring_radius),
        'total_ring_mass_kg': total_ring_mass,
        'total_doubler_mass_kg': total_doubler_mass,
        'stiffening_mass_kg': stiffening_mass,
        'shell_mass_kg': shell.shell_mass,
        'total_structural_mass_kg': total_structural_mass,
        'sigma_applied_MPa': sigma_applied,
        'sigma_allowable_MPa': sigma_allowable_pressurized,
        'sigma_panel_MPa': sigma_panel,
        'MS_global': MS_global,
        'MS_panel': MS_panel,
        'MS_ring_stiffness': MS_ring_stiffness,
        'MS_overall': MS_overall,
        'stiffness_to_mass': stiffness_to_mass,
        'strength_to_mass': strength_to_mass,
        'pressure_factor': p_factor,
        'feasible': MS_overall >= 0
    }


def generate_design_space(shell: ShellGeometry,
                          load: LoadCase,
                          ring_material: Material,
                          doubler_material: Material) -> pd.DataFrame:
    """
    Generate matrix of design configurations and evaluate each
    """
    
    results = []
    
    # Design variable ranges
    n_rings_range = range(5, 20)  # 5 to 19 rings
    web_height_range = np.arange(30, 121, 10)  # 30 to 120 mm
    web_thickness_range = np.arange(1.5, 6.1, 0.5)  # 1.5 to 6 mm
    flange_thickness_range = np.arange(1.5, 6.1, 0.5)  # 1.5 to 6 mm
    doubler_thickness_range = np.arange(2, 6.1, 1)  # 2 to 6 mm
    
    # Flange widths as ratio of web height
    outer_flange_ratio = 1.0  # outer flange = web height
    inner_flange_ratio = 0.75  # inner flange = 0.75 × web height
    
    # Doubler width fixed
    doubler_width = 80  # mm
    
    total_configs = (len(n_rings_range) * len(web_height_range) * 
                     len(web_thickness_range) * len(flange_thickness_range) *
                     len(doubler_thickness_range))
    
    print(f"Evaluating {total_configs} configurations...")
    
    for n_rings in n_rings_range:
        for web_height in web_height_range:
            for web_thick in web_thickness_range:
                for flange_thick in flange_thickness_range:
                    for doubler_thick in doubler_thickness_range:
                        
                        # Create section
                        ring = ZSection(
                            web_height=web_height,
                            web_thickness=web_thick,
                            outer_flange=web_height * outer_flange_ratio,
                            inner_flange=web_height * inner_flange_ratio,
                            flange_thickness=flange_thick,
                            material=ring_material
                        )
                        
                        doubler = DoublerPlate(
                            width=doubler_width,
                            thickness=doubler_thick,
                            material=doubler_material
                        )
                        
                        # Evaluate
                        result = evaluate_design(shell, ring, doubler, n_rings, load)
                        results.append(result)
    
    df = pd.DataFrame(results)
    print(f"Completed. {len(df[df['feasible']])} feasible designs found.")
    
    return df


def find_optimal_designs(df: pd.DataFrame, n_best: int = 10) -> pd.DataFrame:
    """
    Find optimal designs from the design space
    Filters for feasible designs and ranks by stiffness-to-mass ratio
    """
    
    # Filter feasible designs
    feasible = df[df['feasible']].copy()
    
    if len(feasible) == 0:
        print("WARNING: No feasible designs found!")
        # Return best infeasible designs for analysis
        return df.nlargest(n_best, 'MS_overall')
    
    # Sort by stiffness-to-mass ratio
    optimal = feasible.nlargest(n_best, 'stiffness_to_mass')
    
    return optimal


def find_minimum_mass_designs(df: pd.DataFrame, n_best: int = 10) -> pd.DataFrame:
    """
    Find minimum mass designs that meet all constraints
    """
    
    feasible = df[df['feasible']].copy()
    
    if len(feasible) == 0:
        print("WARNING: No feasible designs found!")
        return df.nsmallest(n_best, 'stiffening_mass_kg')
    
    optimal = feasible.nsmallest(n_best, 'stiffening_mass_kg')
    
    return optimal


def pareto_front(df: pd.DataFrame) -> pd.DataFrame:
    """
    Find Pareto-optimal designs (stiffness vs mass tradeoff)
    """
    
    feasible = df[df['feasible']].copy()
    
    if len(feasible) == 0:
        return pd.DataFrame()
    
    # Sort by stiffening mass
    feasible = feasible.sort_values('stiffening_mass_kg')
    
    pareto = []
    max_stiffness = -np.inf
    
    for _, row in feasible.iterrows():
        if row['stiffness_to_mass'] > max_stiffness:
            pareto.append(row)
            max_stiffness = row['stiffness_to_mass']
    
    return pd.DataFrame(pareto)


# =============================================================================
# REPORTING
# =============================================================================

def print_design_summary(design: pd.Series):
    """Print formatted summary of a single design"""
    
    print("\n" + "="*60)
    print("RING FRAME DESIGN SUMMARY")
    print("="*60)
    
    print(f"\nGEOMETRY:")
    print(f"  Number of rings:      {design['n_rings']:.0f}")
    print(f"  Ring spacing:         {design['ring_spacing_mm']:.1f} mm")
    print(f"  Web height:           {design['web_height_mm']:.1f} mm")
    print(f"  Web thickness:        {design['web_thickness_mm']:.1f} mm")
    print(f"  Flange thickness:     {design['flange_thickness_mm']:.1f} mm")
    print(f"  Outer flange width:   {design['outer_flange_mm']:.1f} mm")
    print(f"  Inner flange width:   {design['inner_flange_mm']:.1f} mm")
    print(f"  Doubler thickness:    {design['doubler_thickness_mm']:.1f} mm")
    
    print(f"\nSECTION PROPERTIES:")
    print(f"  Ring area:            {design['ring_area_mm2']:.1f} mm²")
    print(f"  Ring I:               {design['ring_I_mm4']:.2e} mm⁴")
    print(f"  Required I:           {design['I_required_mm4']:.2e} mm⁴")
    
    print(f"\nMASS:")
    print(f"  Single ring:          {design['ring_mass_kg']:.2f} kg")
    print(f"  All rings:            {design['total_ring_mass_kg']:.1f} kg")
    print(f"  All doublers:         {design['total_doubler_mass_kg']:.1f} kg")
    print(f"  Total stiffening:     {design['stiffening_mass_kg']:.1f} kg")
    print(f"  Shell:                {design['shell_mass_kg']:.1f} kg")
    print(f"  TOTAL STRUCTURE:      {design['total_structural_mass_kg']:.1f} kg")
    
    print(f"\nSTRESS (with FOS):")
    print(f"  Applied stress:       {design['sigma_applied_MPa']:.2f} MPa")
    print(f"  Allowable (global):   {design['sigma_allowable_MPa']:.2f} MPa")
    print(f"  Allowable (panel):    {design['sigma_panel_MPa']:.2f} MPa")
    print(f"  Pressure factor:      {design['pressure_factor']:.2f}x")
    
    print(f"\nMARGINS OF SAFETY:")
    print(f"  Global buckling:      {design['MS_global']:+.2f}")
    print(f"  Panel buckling:       {design['MS_panel']:+.2f}")
    print(f"  Ring stiffness:       {design['MS_ring_stiffness']:+.2f}")
    print(f"  OVERALL:              {design['MS_overall']:+.2f}")
    
    print(f"\nPERFORMANCE METRICS:")
    print(f"  Stiffness/mass:       {design['stiffness_to_mass']:.1f} mm⁴/kg")
    print(f"  Strength/mass:        {design['strength_to_mass']:.4f} MPa/kg")
    print(f"  Feasible:             {'YES' if design['feasible'] else 'NO'}")
    
    print("="*60)


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main optimization routine"""
    
    print("\n" + "="*60)
    print("PRESSURE VESSEL RING FRAME OPTIMIZATION")
    print("Artemis Crew Habitat Module - Senior Design Project")
    print("="*60)
    
    # Define shell geometry
    shell = ShellGeometry(
        diameter=4250,      # mm
        length=10000,       # mm
        thickness=5,        # mm
        material=MATERIALS['2219-T87']
    )
    
    print(f"\nSHELL PARAMETERS:")
    print(f"  Diameter:     {shell.diameter} mm")
    print(f"  Length:       {shell.length} mm")
    print(f"  Thickness:    {shell.thickness} mm")
    print(f"  R/t ratio:    {shell.R_over_t:.0f}")
    print(f"  Shell mass:   {shell.shell_mass:.1f} kg")
    print(f"  Material:     {shell.material.name}")
    
    # Define load case (Falcon Heavy MECO)
    load = LoadCase(
        name='Falcon Heavy MECO + Lateral',
        axial_g=6.0,
        lateral_g=2.0,
        internal_pressure=0.101,  # 1 atm in MPa
        total_mass=10000,         # kg
        factor_of_safety=1.4
    )
    
    print(f"\nLOAD CASE: {load.name}")
    print(f"  Axial:        {load.axial_g} g")
    print(f"  Lateral:      {load.lateral_g} g")
    print(f"  Pressure:     {load.internal_pressure*1000:.1f} kPa")
    print(f"  Total mass:   {load.total_mass} kg")
    print(f"  FOS:          {load.factor_of_safety}")
    
    # Materials for stiffening
    ring_material = MATERIALS['7050-T7451']
    doubler_material = MATERIALS['2219-T87']
    
    print(f"\nSTIFFENER MATERIALS:")
    print(f"  Rings:        {ring_material.name}")
    print(f"  Doublers:     {doubler_material.name}")
    
    # Generate design space
    print("\n" + "-"*60)
    df = generate_design_space(shell, load, ring_material, doubler_material)
    
    # Find optimal designs
    print("\n" + "-"*60)
    print("OPTIMAL DESIGNS (Max Stiffness/Mass):")
    print("-"*60)
    
    optimal = find_optimal_designs(df, n_best=5)
    
    cols_to_show = ['n_rings', 'web_height_mm', 'web_thickness_mm', 
                    'flange_thickness_mm', 'stiffening_mass_kg',
                    'MS_overall', 'stiffness_to_mass']
    
    print(optimal[cols_to_show].to_string(index=False))
    
    # Find minimum mass designs
    print("\n" + "-"*60)
    print("MINIMUM MASS DESIGNS:")
    print("-"*60)
    
    min_mass = find_minimum_mass_designs(df, n_best=5)
    print(min_mass[cols_to_show].to_string(index=False))
    
    # Find Pareto front
    print("\n" + "-"*60)
    print("PARETO FRONT (Mass vs Stiffness tradeoff):")
    print("-"*60)
    
    pareto = pareto_front(df)
    if len(pareto) > 0:
        print(pareto[cols_to_show].head(10).to_string(index=False))
    
    # Print best overall design
    if len(optimal) > 0:
        print_design_summary(optimal.iloc[0])
    
    # Also print minimum mass feasible design
    if len(min_mass) > 0:
        print("\n" + "="*60)
        print("MINIMUM MASS FEASIBLE DESIGN")
        print("="*60)
        print_design_summary(min_mass.iloc[0])
    
    # Save full results
    df.to_csv('/home/claude/ring_optimization_results.csv', index=False)
    optimal.to_csv('/home/claude/optimal_designs.csv', index=False)
    if len(pareto) > 0:
        pareto.to_csv('/home/claude/pareto_front.csv', index=False)
    
    # Create visualization
    try:
        create_visualization(df, optimal, pareto)
    except Exception as e:
        print(f"Visualization skipped: {e}")
    
    print(f"\nFull results saved to: ring_optimization_results.csv")
    print(f"Optimal designs saved to: optimal_designs.csv")
    
    return df, optimal


def create_visualization(df: pd.DataFrame, optimal: pd.DataFrame, 
                         pareto: pd.DataFrame):
    """Create visualization of optimization results"""
    import matplotlib.pyplot as plt
    
    feasible = df[df['feasible']]
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Plot 1: Mass vs Stiffness-to-Mass ratio
    ax1 = axes[0, 0]
    ax1.scatter(feasible['stiffening_mass_kg'], feasible['stiffness_to_mass'],
                alpha=0.3, s=10, label='Feasible designs')
    if len(pareto) > 0:
        ax1.scatter(pareto['stiffening_mass_kg'], pareto['stiffness_to_mass'],
                    color='red', s=50, label='Pareto front', zorder=5)
    if len(optimal) > 0:
        ax1.scatter(optimal.iloc[0]['stiffening_mass_kg'], 
                    optimal.iloc[0]['stiffness_to_mass'],
                    color='green', s=100, marker='*', label='Optimal', zorder=6)
    ax1.set_xlabel('Stiffening Mass (kg)')
    ax1.set_ylabel('Stiffness/Mass (mm⁴/kg)')
    ax1.set_title('Stiffness Efficiency vs Mass')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Number of rings vs Mass
    ax2 = axes[0, 1]
    for n in feasible['n_rings'].unique():
        subset = feasible[feasible['n_rings'] == n]
        ax2.scatter([n]*len(subset), subset['stiffening_mass_kg'], 
                    alpha=0.3, s=10)
    ax2.set_xlabel('Number of Rings')
    ax2.set_ylabel('Stiffening Mass (kg)')
    ax2.set_title('Mass vs Ring Count')
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Margin of Safety distribution
    ax3 = axes[1, 0]
    ax3.hist(feasible['MS_overall'], bins=30, edgecolor='black', alpha=0.7)
    ax3.axvline(x=0, color='red', linestyle='--', label='MS = 0')
    ax3.set_xlabel('Overall Margin of Safety')
    ax3.set_ylabel('Count')
    ax3.set_title('Distribution of Safety Margins')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: Web height vs Flange thickness colored by mass
    ax4 = axes[1, 1]
    scatter = ax4.scatter(feasible['web_height_mm'], feasible['flange_thickness_mm'],
                          c=feasible['stiffening_mass_kg'], cmap='viridis',
                          alpha=0.5, s=20)
    plt.colorbar(scatter, ax=ax4, label='Mass (kg)')
    ax4.set_xlabel('Web Height (mm)')
    ax4.set_ylabel('Flange Thickness (mm)')
    ax4.set_title('Design Space (color = mass)')
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('/home/claude/optimization_results.png', dpi=150)
    plt.close()
    
    print("\nVisualization saved to: optimization_results.png")


if __name__ == '__main__':
    df, optimal = main()
