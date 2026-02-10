#!/usr/bin/env python3
"""
Lunar/Mars Habitat Module - Structural Analysis Calculator
NASA Design Challenge TDC-106
Team Design Tool for Quick Calculations and Parametric Studies
"""

import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Tuple, Dict

@dataclass
class ModuleGeometry:
    """Habitat module geometry parameters"""
    outer_diameter: float  # meters
    wall_thickness: float  # meters
    length: float  # meters
    num_legs: int
    
    @property
    def inner_diameter(self):
        return self.outer_diameter - 2 * self.wall_thickness
    
    @property
    def mean_radius(self):
        return (self.outer_diameter - self.wall_thickness) / 2
    
    @property
    def cross_sectional_area(self):
        """Cross-sectional area of cylinder wall"""
        r_o = self.outer_diameter / 2
        r_i = self.inner_diameter / 2
        return np.pi * (r_o**2 - r_i**2)
    
    @property
    def volume_material(self):
        """Volume of material in cylinder shell"""
        return self.cross_sectional_area * self.length
    
    @property
    def internal_volume(self):
        """Internal habitable volume"""
        return np.pi * (self.inner_diameter/2)**2 * self.length

@dataclass
class Material2219T87:
    """Aluminum 2219-T87 material properties"""
    yield_strength: float = 395e6  # Pa
    ultimate_strength: float = 475e6  # Pa
    elastic_modulus: float = 73.8e9  # Pa
    poissons_ratio: float = 0.33
    density: float = 2840  # kg/m³
    cte: float = 22.3e-6  # /°C
    allowable_stress_yield: float = 395e6 / 1.5  # With safety factor
    allowable_stress_ultimate: float = 475e6 / 2.0  # With safety factor

class HabitatModuleAnalysis:
    def __init__(self, geometry: ModuleGeometry, material: Material2219T87):
        self.geom = geometry
        self.mat = material
        self.pressure_internal = 101325  # Pa (1 atm)
        self.pressure_external_mars = 600  # Pa
        self.pressure_external_lunar = 1e-10  # Pa (vacuum)
        
    def calculate_mass(self, include_endcaps: bool = True) -> Dict[str, float]:
        """Calculate module mass breakdown"""
        shell_mass = self.geom.volume_material * self.mat.density
        
        if include_endcaps:
            # Approximate hemispherical end caps
            endcap_mass = 2 * (2/3) * np.pi * ((self.geom.outer_diameter/2)**3 - 
                                                (self.geom.inner_diameter/2)**3) * self.mat.density
        else:
            endcap_mass = 0
            
        # Estimate leg mass (conservative)
        leg_mass = self.geom.num_legs * 100  # kg per leg
        
        return {
            'shell': shell_mass,
            'endcaps': endcap_mass,
            'legs': leg_mass,
            'total_structure': shell_mass + endcap_mass + leg_mass
        }
    
    def pressure_stress_analysis(self) -> Dict[str, float]:
        """Calculate pressure-induced stresses"""
        p = self.pressure_internal
        r = self.geom.mean_radius
        t = self.geom.wall_thickness
        
        # Thin-wall pressure vessel equations
        hoop_stress = (p * r) / t
        longitudinal_stress = (p * r) / (2 * t)
        
        # Von Mises equivalent stress
        von_mises = np.sqrt(hoop_stress**2 + longitudinal_stress**2 - 
                           hoop_stress * longitudinal_stress)
        
        # Safety factors
        sf_yield = self.mat.yield_strength / von_mises
        sf_ultimate = self.mat.ultimate_strength / von_mises
        
        return {
            'hoop_stress': hoop_stress,
            'longitudinal_stress': longitudinal_stress,
            'von_mises_stress': von_mises,
            'safety_factor_yield': sf_yield,
            'safety_factor_ultimate': sf_ultimate,
            'pressure_vessel_requirement_met': sf_yield >= 2.5 and sf_ultimate >= 4.0
        }
    
    def buckling_analysis(self) -> Dict[str, float]:
        """Calculate critical buckling pressure for external loading"""
        E = self.mat.elastic_modulus
        nu = self.mat.poissons_ratio
        t = self.geom.wall_thickness
        D = self.geom.outer_diameter
        
        # NASA SP-8007 formula for cylindrical shells
        # Conservative estimate for simply supported ends
        K = 0.856  # Knockdown factor for imperfections
        n = 2  # Number of circumferential waves (typically 2-4)
        
        # Critical buckling pressure (external)
        p_cr = K * (2.42 * E * (t/D)**2.5) / np.sqrt(1 - nu**2)
        
        # Safety factors
        sf_mars = p_cr / self.pressure_external_mars if self.pressure_external_mars > 0 else float('inf')
        
        # Check for depressurization scenario
        depressurization_pressure = self.pressure_internal  # Worst case: full vacuum inside
        
        return {
            'critical_buckling_pressure': p_cr,
            'safety_factor_mars': sf_mars,
            'buckling_safe_mars': sf_mars > 3.0,
            'minimum_thickness_required': self._minimum_thickness_for_buckling()
        }
    
    def _minimum_thickness_for_buckling(self, safety_factor: float = 3.0) -> float:
        """Calculate minimum thickness to prevent buckling"""
        E = self.mat.elastic_modulus
        nu = self.mat.poissons_ratio
        D = self.geom.outer_diameter
        p_required = self.pressure_internal * safety_factor  # Conservative
        K = 0.856
        
        # Rearrange buckling formula to solve for thickness
        t_min = D * (p_required * np.sqrt(1 - nu**2) / (K * 2.42 * E))**(1/2.5)
        return t_min * 1000  # Convert to mm
    
    def launch_loads_analysis(self, g_load: float = 6.0) -> Dict[str, float]:
        """Analyze stresses during launch"""
        mass = self.calculate_mass()
        total_mass = 10000  # kg (maximum allowed)
        
        # Axial load from acceleration
        F_axial = g_load * 9.81 * total_mass  # N
        
        # Stress in cylinder wall
        A_wall = np.pi * self.geom.outer_diameter * self.geom.wall_thickness
        axial_stress = F_axial / A_wall
        
        # Combined with pressure stresses
        pressure_stresses = self.pressure_stress_analysis()
        
        # Conservative combined stress (von Mises)
        combined_stress = np.sqrt(
            axial_stress**2 + 
            pressure_stresses['hoop_stress']**2 + 
            pressure_stresses['longitudinal_stress']**2
        )
        
        return {
            'axial_force': F_axial,
            'axial_stress': axial_stress,
            'combined_stress_launch': combined_stress,
            'safety_factor': self.mat.yield_strength / combined_stress,
            'launch_loads_safe': combined_stress < self.mat.allowable_stress_yield
        }
    
    def thermal_stress_analysis(self, delta_T: float = 300) -> Dict[str, float]:
        """Calculate thermal stresses"""
        E = self.mat.elastic_modulus
        alpha = self.mat.cte
        
        # Stress if fully constrained
        thermal_stress_max = E * alpha * delta_T
        
        # With proper mounting (assume 50% constraint)
        thermal_stress_realistic = 0.5 * thermal_stress_max
        
        # Combined with operational stresses
        pressure_stresses = self.pressure_stress_analysis()
        combined = pressure_stresses['von_mises_stress'] + thermal_stress_realistic
        
        return {
            'thermal_stress_max': thermal_stress_max,
            'thermal_stress_realistic': thermal_stress_realistic,
            'combined_with_pressure': combined,
            'requires_expansion_joints': thermal_stress_max > self.mat.yield_strength,
            'safety_factor_combined': self.mat.yield_strength / combined
        }
    
    def leg_loads_analysis(self) -> Dict[str, Tuple[float, float]]:
        """Calculate loads on support legs"""
        mass = self.calculate_mass()
        total_mass = 10000  # kg
        
        loads = {}
        
        # Earth launch (6g)
        loads['earth_launch_6g'] = (
            6 * 9.81 * total_mass / self.geom.num_legs,
            'Vertical load per leg during launch'
        )
        
        # Lunar surface
        loads['lunar_operation'] = (
            1.62 * total_mass / self.geom.num_legs,
            'Vertical load per leg on Moon'
        )
        
        # Mars surface
        loads['mars_operation'] = (
            3.71 * total_mass / self.geom.num_legs,
            'Vertical load per leg on Mars'
        )
        
        # Landing impact (3g)
        loads['landing_impact'] = (
            3 * 3.71 * total_mass / self.geom.num_legs,
            'Impact load per leg during Mars landing'
        )
        
        return loads
    
    def generate_summary_report(self) -> str:
        """Generate comprehensive analysis summary"""
        mass = self.calculate_mass()
        pressure = self.pressure_stress_analysis()
        buckling = self.buckling_analysis()
        launch = self.launch_loads_analysis()
        thermal = self.thermal_stress_analysis()
        legs = self.leg_loads_analysis()
        
        report = f"""
HABITAT MODULE STRUCTURAL ANALYSIS SUMMARY
{'='*50}

GEOMETRY:
- Outer Diameter: {self.geom.outer_diameter:.2f} m
- Wall Thickness: {self.geom.wall_thickness*1000:.1f} mm
- Length: {self.geom.length:.1f} m
- Internal Volume: {self.geom.internal_volume:.1f} m³
- Number of Legs: {self.geom.num_legs}

MASS BREAKDOWN:
- Shell Mass: {mass['shell']:.0f} kg
- End Caps: {mass['endcaps']:.0f} kg
- Legs: {mass['legs']:.0f} kg
- Total Structure: {mass['total_structure']:.0f} kg
- Mass Margin: {10000 - mass['total_structure']:.0f} kg available

PRESSURE STRESS ANALYSIS:
- Hoop Stress: {pressure['hoop_stress']/1e6:.1f} MPa
- Longitudinal Stress: {pressure['longitudinal_stress']/1e6:.1f} MPa
- Von Mises Stress: {pressure['von_mises_stress']/1e6:.1f} MPa
- Safety Factor (Yield): {pressure['safety_factor_yield']:.1f}
- Safety Factor (Ultimate): {pressure['safety_factor_ultimate']:.1f}
- NASA Requirement Met: {'✅ YES' if pressure['pressure_vessel_requirement_met'] else '❌ NO'}

BUCKLING ANALYSIS:
- Critical Buckling Pressure: {buckling['critical_buckling_pressure']:.0f} Pa
- Safety Factor (Mars): {buckling['safety_factor_mars']:.1f}
- Buckling Safe: {'✅ YES' if buckling['buckling_safe_mars'] else '❌ NO'}
- Min Thickness for Buckling: {buckling['minimum_thickness_required']:.2f} mm

LAUNCH LOADS:
- Axial Force (6g): {launch['axial_force']/1e3:.0f} kN
- Combined Stress: {launch['combined_stress_launch']/1e6:.1f} MPa
- Safety Factor: {launch['safety_factor']:.1f}
- Launch Safe: {'✅ YES' if launch['launch_loads_safe'] else '❌ NO'}

THERMAL ANALYSIS:
- Max Thermal Stress (constrained): {thermal['thermal_stress_max']/1e6:.0f} MPa
- Realistic Thermal Stress: {thermal['thermal_stress_realistic']/1e6:.0f} MPa
- Combined with Pressure: {thermal['combined_with_pressure']/1e6:.1f} MPa
- Safety Factor: {thermal['safety_factor_combined']:.1f}
- Expansion Joints Required: {'YES' if thermal['requires_expansion_joints'] else 'NO'}

LEG LOADS:
- Earth Launch (per leg): {legs['earth_launch_6g'][0]/1e3:.0f} kN
- Lunar Operation (per leg): {legs['lunar_operation'][0]/1e3:.1f} kN
- Mars Operation (per leg): {legs['mars_operation'][0]/1e3:.1f} kN
- Landing Impact (per leg): {legs['landing_impact'][0]/1e3:.0f} kN

{'='*50}
"""
        return report

def parametric_study():
    """Run parametric study on wall thickness"""
    thicknesses = np.linspace(3, 10, 50) / 1000  # 3mm to 10mm
    results = {
        'thickness': [],
        'mass': [],
        'von_mises': [],
        'sf_yield': [],
        'buckling_pressure': []
    }
    
    material = Material2219T87()
    
    for t in thicknesses:
        geom = ModuleGeometry(
            outer_diameter=4.25,
            wall_thickness=t,
            length=10.0,
            num_legs=4
        )
        
        analyzer = HabitatModuleAnalysis(geom, material)
        mass = analyzer.calculate_mass()
        pressure = analyzer.pressure_stress_analysis()
        buckling = analyzer.buckling_analysis()
        
        results['thickness'].append(t * 1000)  # Convert to mm
        results['mass'].append(mass['total_structure'])
        results['von_mises'].append(pressure['von_mises_stress'] / 1e6)  # MPa
        results['sf_yield'].append(pressure['safety_factor_yield'])
        results['buckling_pressure'].append(buckling['critical_buckling_pressure'])
    
    # Create plots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
    
    # Mass vs Thickness
    ax1.plot(results['thickness'], results['mass'], 'b-', linewidth=2)
    ax1.axhline(y=10000, color='r', linestyle='--', label='10,000 kg limit')
    ax1.set_xlabel('Wall Thickness (mm)')
    ax1.set_ylabel('Total Mass (kg)')
    ax1.set_title('Structural Mass vs Wall Thickness')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Von Mises Stress vs Thickness
    ax2.plot(results['thickness'], results['von_mises'], 'g-', linewidth=2)
    ax2.axhline(y=395, color='r', linestyle='--', label='Yield Strength')
    ax2.set_xlabel('Wall Thickness (mm)')
    ax2.set_ylabel('Von Mises Stress (MPa)')
    ax2.set_title('Pressure Stress vs Wall Thickness')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    # Safety Factor vs Thickness
    ax3.plot(results['thickness'], results['sf_yield'], 'orange', linewidth=2)
    ax3.axhline(y=2.5, color='g', linestyle='--', label='Min SF (Yield)')
    ax3.axhline(y=4.0, color='b', linestyle='--', label='Min SF (Ultimate)')
    ax3.set_xlabel('Wall Thickness (mm)')
    ax3.set_ylabel('Safety Factor')
    ax3.set_title('Safety Factor vs Wall Thickness')
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    # Buckling Pressure vs Thickness
    ax4.plot(results['thickness'], results['buckling_pressure'], 'm-', linewidth=2)
    ax4.axhline(y=101325, color='r', linestyle='--', label='1 atm pressure')
    ax4.set_xlabel('Wall Thickness (mm)')
    ax4.set_ylabel('Critical Buckling Pressure (Pa)')
    ax4.set_title('Buckling Resistance vs Wall Thickness')
    ax4.set_yscale('log')
    ax4.grid(True, alpha=0.3)
    ax4.legend()
    
    plt.suptitle('Habitat Module Parametric Study - Wall Thickness Optimization', fontsize=14, fontweight='bold')
    plt.tight_layout()
    from pathlib import Path
    output_dir = Path.home() / "Documents"
    output_file = output_dir / "parametric_study.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.show()
    
    # Find optimal thickness
    valid_indices = [i for i, sf in enumerate(results['sf_yield']) if sf >= 2.5]
    if valid_indices:
        optimal_idx = valid_indices[0]  # Minimum thickness that meets requirements
        print(f"\nOPTIMAL THICKNESS: {results['thickness'][optimal_idx]:.1f} mm")
        print(f"  - Mass: {results['mass'][optimal_idx]:.0f} kg")
        print(f"  - Safety Factor: {results['sf_yield'][optimal_idx]:.1f}")
        print(f"  - Von Mises Stress: {results['von_mises'][optimal_idx]:.1f} MPa")

def main():
    """Main analysis for current design"""
    # Current design configuration
    geometry = ModuleGeometry(
        outer_diameter=4.25,
        wall_thickness=0.005,
        length=10.0,
        num_legs=4
    )
    
    material = Material2219T87()
    analyzer = HabitatModuleAnalysis(geometry, material)
    
    # Generate and print report
    print(analyzer.generate_summary_report())
    
    # Run parametric study
    print("\nRunning parametric study on wall thickness...")
    parametric_study()
    
    # Additional trade studies
    print("\n" + "="*50)
    print("TRADE STUDY: 4 LEGS vs 6 LEGS")
    print("="*50)
    
    for num_legs in [4, 6]:
        geom_legs = ModuleGeometry(
            outer_diameter=4.25,
            wall_thickness=0.005,
            length=10.0,
            num_legs=num_legs
        )
        analyzer_legs = HabitatModuleAnalysis(geom_legs, material)
        legs = analyzer_legs.leg_loads_analysis()
        
        print(f"\n{num_legs} LEGS Configuration:")
        for load_case, (force, description) in legs.items():
            print(f"  {load_case}: {force/1e3:.1f} kN per leg")

if __name__ == "__main__":
    main()
