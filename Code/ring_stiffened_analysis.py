#!/usr/bin/env python3
"""
Ring-Stiffened Habitat Module Analysis Tool
NASA Design Challenge TDC-106
Analysis for hybrid 2219-T87 shell with 7050 aluminum ring frames
"""

import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from dataclasses import field
from typing import Dict, List, Tuple
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch

@dataclass
class Material2219T87:
    """2219-T87 Aluminum for pressure shell"""
    name: str = "2219-T87"
    yield_strength: float = 395e6  # Pa
    ultimate_strength: float = 475e6  # Pa
    elastic_modulus: float = 73.8e9  # Pa
    poissons_ratio: float = 0.33
    density: float = 2840  # kg/m³
    cte: float = 22.3e-6  # /°C
    fatigue_strength: float = 105e6  # Pa at 10^8 cycles

@dataclass
class Material7050T7451:
    """7050-T7451 Aluminum for ring frames"""
    name: str = "7050-T7451"
    yield_strength: float = 490e6  # Pa
    ultimate_strength: float = 545e6  # Pa
    elastic_modulus: float = 71.7e9  # Pa
    poissons_ratio: float = 0.33
    density: float = 2830  # kg/m³
    cte: float = 23.6e-6  # /°C
    fatigue_strength: float = 160e6  # Pa at 10^8 cycles

@dataclass
class RingFrameGeometry:
    """T-section ring frame dimensions"""
    web_height: float  # meters
    web_thickness: float  # meters
    flange_width: float  # meters
    flange_thickness: float  # meters
    
    @property
    def area(self):
        """Cross-sectional area of T-section"""
        area_web = self.web_height * self.web_thickness
        area_flange = self.flange_width * self.flange_thickness
        return area_web + area_flange
    
    @property
    def centroid_y(self):
        """Centroid location from bottom of web"""
        A_web = self.web_height * self.web_thickness
        A_flange = self.flange_width * self.flange_thickness
        y_web = self.web_height / 2
        y_flange = self.web_height + self.flange_thickness / 2
        return (A_web * y_web + A_flange * y_flange) / (A_web + A_flange)
    
    @property
    def moment_of_inertia(self):
        """Second moment of area about centroidal axis"""
        yc = self.centroid_y
        # Web contribution
        I_web = (self.web_thickness * self.web_height**3) / 12
        A_web = self.web_height * self.web_thickness
        d_web = abs(self.web_height/2 - yc)
        I_web_total = I_web + A_web * d_web**2
        
        # Flange contribution
        I_flange = (self.flange_width * self.flange_thickness**3) / 12
        A_flange = self.flange_width * self.flange_thickness
        d_flange = abs(self.web_height + self.flange_thickness/2 - yc)
        I_flange_total = I_flange + A_flange * d_flange**2
        
        return I_web_total + I_flange_total
    
    @property
    def section_modulus(self):
        """Section modulus (minimum)"""
        yc = self.centroid_y
        c_max = max(yc, self.web_height + self.flange_thickness - yc)
        return self.moment_of_inertia / c_max

@dataclass
class RingStiffenedModule:
    """Complete ring-stiffened habitat module"""
    # Shell geometry
    outer_diameter: float = 4.25  # m
    shell_thickness: float = 0.005  # m
    length: float = 10.0  # m
    
    # Ring configuration
    num_rings: int = 5
    ring_frame: RingFrameGeometry = None
    
    # Stringer configuration
    num_stringers: int = 8
    stringer_area: float = 475e-6  # m² (L50x50x5)
    
    # Materials
    shell_material: Material2219T87 = field(default_factory=Material2219T87)
    ring_material: Material7050T7451 = field(default_factory=Material7050T7451)
    
    def __post_init__(self):
        if self.ring_frame is None:
            self.ring_frame = RingFrameGeometry(
                web_height=0.150,
                web_thickness=0.008,
                flange_width=0.100,
                flange_thickness=0.012
            )
    
    @property
    def ring_spacing(self):
        """Spacing between rings"""
        return self.length / (self.num_rings + 1)
    
    @property
    def shell_radius(self):
        """Mean radius of shell"""
        return (self.outer_diameter - self.shell_thickness) / 2
    
    def calculate_mass_breakdown(self) -> Dict[str, float]:
        """Calculate detailed mass breakdown"""
        # Shell mass
        shell_volume = np.pi * ((self.outer_diameter/2)**2 - 
                                (self.outer_diameter/2 - self.shell_thickness)**2) * self.length
        shell_mass = shell_volume * self.shell_material.density
        
        # End caps (hemispherical approximation)
        endcap_volume = (4/3) * np.pi * ((self.outer_diameter/2)**3 - 
                                         (self.outer_diameter/2 - self.shell_thickness)**3)
        endcap_mass = endcap_volume * self.shell_material.density
        
        # Ring frames
        ring_mass_single = self.ring_frame.area * np.pi * self.outer_diameter * self.ring_material.density
        rings_mass = ring_mass_single * self.num_rings
        
        # Stringers
        stringer_length = self.length
        stringer_mass_single = self.stringer_area * stringer_length * self.ring_material.density
        stringers_mass = stringer_mass_single * self.num_stringers
        
        # Floor structure (estimate)
        floor_area = np.pi * (self.outer_diameter/2 - 0.1)**2 * 0.003  # 3mm equivalent thickness
        floor_mass = floor_area * self.length * self.ring_material.density
        
        return {
            'shell': shell_mass,
            'endcaps': endcap_mass,
            'rings': rings_mass,
            'stringers': stringers_mass,
            'floor': floor_mass,
            'connections': 50,  # kg, estimated
            'legs': 400,  # kg, estimated
            'insulation': 150,  # kg, MLI
            'total': shell_mass + endcap_mass + rings_mass + stringers_mass + 
                    floor_mass + 50 + 400 + 150
        }
    
    def thermal_expansion_analysis(self, delta_T: float = 300) -> Dict[str, float]:
        """Analyze thermal expansion and clearances needed"""
        # Shell expansion
        shell_radial_expansion = self.shell_radius * self.shell_material.cte * delta_T
        shell_length_expansion = self.length * self.shell_material.cte * delta_T
        
        # Ring expansion (different CTE!)
        ring_radial_expansion = self.shell_radius * self.ring_material.cte * delta_T
        
        # Differential expansion
        differential_radial = abs(shell_radial_expansion - ring_radial_expansion)
        
        # Required clearance (with safety factor)
        required_clearance = differential_radial * 1.5
        
        return {
            'shell_radial_expansion_mm': shell_radial_expansion * 1000,
            'shell_length_expansion_mm': shell_length_expansion * 1000,
            'ring_radial_expansion_mm': ring_radial_expansion * 1000,
            'differential_expansion_mm': differential_radial * 1000,
            'required_clearance_mm': required_clearance * 1000,
            'sliding_joint_feasible': required_clearance < 0.010  # 10mm max
        }
    
    def ring_stress_analysis(self, pressure: float = 101325) -> Dict[str, float]:
        """Analyze stresses in ring frames"""
        R = self.shell_radius
        
        # Hoop compression in ring from internal pressure
        N_ring = pressure * R  # Force per unit length
        
        # Bending moment in ring (approximate)
        M_max = pressure * R**2 / 4
        
        # Direct stress
        sigma_direct = N_ring / self.ring_frame.area
        
        # Bending stress
        sigma_bending = M_max / self.ring_frame.section_modulus
        
        # Combined stress
        sigma_combined = abs(sigma_direct) + abs(sigma_bending)
        
        # Safety factors
        sf_yield = self.ring_material.yield_strength / sigma_combined
        sf_ultimate = self.ring_material.ultimate_strength / sigma_combined
        
        # Equipment load capacity (per ring)
        floor_load = 2400  # Pa (2.4 kPa)
        floor_area_per_bay = np.pi * R**2
        equipment_load_per_ring = floor_load * floor_area_per_bay
        
        return {
            'hoop_force_N_per_m': N_ring,
            'max_moment_Nm': M_max,
            'direct_stress_MPa': sigma_direct / 1e6,
            'bending_stress_MPa': sigma_bending / 1e6,
            'combined_stress_MPa': sigma_combined / 1e6,
            'safety_factor_yield': sf_yield,
            'safety_factor_ultimate': sf_ultimate,
            'equipment_capacity_kg': equipment_load_per_ring / 9.81,
            'stress_acceptable': sf_yield > 1.5
        }
    
    def buckling_analysis_with_rings(self) -> Dict[str, float]:
        """Analyze buckling resistance with ring stiffeners"""
        E = self.shell_material.elastic_modulus
        nu = self.shell_material.poissons_ratio
        t = self.shell_thickness
        R = self.shell_radius
        L = self.ring_spacing
        
        # Effective moment of inertia (shell + rings + stringers)
        I_shell = t**3 / 12  # per unit width
        
        # Ring contribution (smeared)
        I_ring_contribution = (self.ring_frame.moment_of_inertia * self.num_rings) / self.length
        
        # Stringer contribution
        stringer_radius_offset = 0.02  # m from shell
        I_stringer_contribution = self.num_stringers * self.stringer_area * stringer_radius_offset**2
        
        # Total effective properties
        EI_effective = E * t * R + \
                      self.ring_material.elastic_modulus * I_ring_contribution + \
                      self.ring_material.elastic_modulus * I_stringer_contribution / (2 * np.pi * R)
        
        # Critical buckling pressure (NASA SP-8007 modified for stiffened shells)
        # Using Donnell's equation for ring-stiffened cylinders
        n = 2  # Number of circumferential waves
        m = 1  # Number of axial half-waves
        
        # Simplified formula for ring-stiffened cylinder
        K = 0.856  # Knockdown factor
        geometry_factor = (t/R)**2.5 * (1 + 50 * I_ring_contribution/t**3)**0.5
        
        P_cr = K * 0.6 * E * geometry_factor
        
        # Safety factors
        sf_vacuum = P_cr / 101325  # Against full vacuum outside
        sf_depressurization = P_cr / 101325  # Against sudden depressurization
        
        # Compare to unstiffened shell
        P_cr_unstiffened = K * 0.6 * E * (t/R)**2.5
        improvement_factor = P_cr / P_cr_unstiffened
        
        return {
            'critical_pressure_kPa': P_cr / 1000,
            'safety_factor_vacuum': sf_vacuum,
            'safety_factor_depressurization': sf_depressurization,
            'improvement_over_unstiffened': improvement_factor,
            'buckling_acceptable': sf_vacuum > 1.5,
            'recommendation': 'Add stringers' if sf_vacuum < 1.5 else 'Design adequate'
        }
    
    def connection_design(self) -> Dict[str, any]:
        """Design sliding connections between rings and shell"""
        # Load transfer requirements
        pressure = 101325  # Pa
        R = self.shell_radius
        
        # Radial load from pressure (per ring)
        F_radial = pressure * np.pi * R**2
        
        # Number of connection points per ring
        num_connections = 24  # Every 15 degrees
        
        # Load per connection
        F_per_connection = F_radial / num_connections
        
        # Shear stress in connection (assuming M8 pin)
        pin_diameter = 0.008  # m
        pin_area = np.pi * (pin_diameter/2)**2
        tau_pin = F_per_connection / pin_area
        
        # Bearing stress (assuming aluminum)
        bearing_area = pin_diameter * self.shell_thickness
        sigma_bearing = F_per_connection / bearing_area
        
        # Thermal expansion clearance needed
        thermal_data = self.thermal_expansion_analysis()
        slot_length = thermal_data['required_clearance_mm'] + 5  # mm, with margin
        
        return {
            'connections_per_ring': num_connections,
            'load_per_connection_kN': F_per_connection / 1000,
            'pin_shear_stress_MPa': tau_pin / 1e6,
            'bearing_stress_MPa': sigma_bearing / 1e6,
            'slot_length_mm': slot_length,
            'slot_width_mm': pin_diameter * 1000 + 1,  # 1mm clearance
            'connection_type': 'Radial sliding slot',
            'material': 'Ti-6Al-4V pins with PTFE bushings'
        }

def visualize_ring_configuration(module: RingStiffenedModule):
    """Create visualization of ring-stiffened module configuration"""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # 1. Side view of module with rings
    ax1 = axes[0, 0]
    ax1.set_title('Side View - Ring Configuration', fontweight='bold')
    
    # Draw cylinder outline
    cylinder = Rectangle((-module.length/2, -module.outer_diameter/2), 
                        module.length, module.outer_diameter,
                        fill=False, edgecolor='blue', linewidth=2)
    ax1.add_patch(cylinder)
    
    # Draw rings
    ring_positions = np.linspace(-module.length/2 + module.ring_spacing, 
                                module.length/2 - module.ring_spacing, 
                                module.num_rings)
    for x_pos in ring_positions:
        ring = Rectangle((x_pos - 0.05, -module.outer_diameter/2 - 0.15), 
                        0.1, module.outer_diameter + 0.3,
                        fill=True, facecolor='red', alpha=0.7, edgecolor='darkred')
        ax1.add_patch(ring)
    
    # Draw stringers
    stringer_y_positions = np.linspace(-module.outer_diameter/2 + 0.1, 
                                       module.outer_diameter/2 - 0.1, 
                                       module.num_stringers//2)
    for y_pos in stringer_y_positions:
        ax1.plot([-module.length/2, module.length/2], [y_pos, y_pos], 
                'g-', linewidth=1, alpha=0.5)
        ax1.plot([-module.length/2, module.length/2], [-y_pos, -y_pos], 
                'g-', linewidth=1, alpha=0.5)
    
    ax1.set_xlim(-module.length/2 - 1, module.length/2 + 1)
    ax1.set_ylim(-module.outer_diameter/2 - 0.5, module.outer_diameter/2 + 0.5)
    ax1.set_xlabel('Length (m)')
    ax1.set_ylabel('Diameter (m)')
    ax1.grid(True, alpha=0.3)
    ax1.set_aspect('equal')
    
    # 2. Cross-section view
    ax2 = axes[0, 1]
    ax2.set_title('Cross-Section View', fontweight='bold')
    
    # Draw shell circle
    shell_outer = Circle((0, 0), module.outer_diameter/2, 
                         fill=False, edgecolor='blue', linewidth=2)
    shell_inner = Circle((0, 0), module.outer_diameter/2 - module.shell_thickness, 
                         fill=False, edgecolor='blue', linewidth=1, linestyle='--')
    ax2.add_patch(shell_outer)
    ax2.add_patch(shell_inner)
    
    # Draw ring frame (T-section representation)
    ring_circle = Circle((0, 0), module.outer_diameter/2 - module.shell_thickness - 0.01,
                         fill=False, edgecolor='red', linewidth=4)
    ax2.add_patch(ring_circle)
    
    # Draw stringers
    angles = np.linspace(0, 2*np.pi, module.num_stringers, endpoint=False)
    for angle in angles:
        x = (module.outer_diameter/2 - module.shell_thickness - 0.02) * np.cos(angle)
        y = (module.outer_diameter/2 - module.shell_thickness - 0.02) * np.sin(angle)
        stringer = Circle((x, y), 0.05, fill=True, facecolor='green', alpha=0.7)
        ax2.add_patch(stringer)
    
    # Draw floor
    ax2.plot([-module.outer_diameter/2 + 0.3, module.outer_diameter/2 - 0.3], 
            [-0.5, -0.5], 'brown', linewidth=3, label='Floor Grid')
    
    ax2.set_xlim(-module.outer_diameter/2 - 0.5, module.outer_diameter/2 + 0.5)
    ax2.set_ylim(-module.outer_diameter/2 - 0.5, module.outer_diameter/2 + 0.5)
    ax2.set_xlabel('Width (m)')
    ax2.set_ylabel('Height (m)')
    ax2.grid(True, alpha=0.3)
    ax2.set_aspect('equal')
    ax2.legend()
    
    # 3. Ring frame detail
    ax3 = axes[1, 0]
    ax3.set_title('T-Section Ring Frame Detail', fontweight='bold')
    
    rf = module.ring_frame
    
    # Draw T-section
    # Web
    web = Rectangle((0, 0), rf.web_thickness*1000, rf.web_height*1000,
                   fill=True, facecolor='red', alpha=0.8, edgecolor='darkred')
    ax3.add_patch(web)
    
    # Flange
    flange = Rectangle((-((rf.flange_width*1000 - rf.web_thickness*1000)/2), rf.web_height*1000),
                      rf.flange_width*1000, rf.flange_thickness*1000,
                      fill=True, facecolor='red', alpha=0.8, edgecolor='darkred')
    ax3.add_patch(flange)
    
    # Dimensions
    ax3.annotate(f'{rf.web_height*1000:.0f} mm', 
                xy=(rf.web_thickness*1000 + 5, rf.web_height*1000/2),
                fontsize=10, ha='left')
    ax3.annotate(f'{rf.flange_width*1000:.0f} mm',
                xy=(0, rf.web_height*1000 + rf.flange_thickness*1000 + 5),
                fontsize=10, ha='center')
    ax3.annotate(f'{rf.web_thickness*1000:.0f} mm',
                xy=(rf.web_thickness*1000/2, -10),
                fontsize=10, ha='center')
    ax3.annotate(f'{rf.flange_thickness*1000:.0f} mm',
                xy=(rf.flange_width*1000 + 5, rf.web_height*1000 + rf.flange_thickness*1000/2),
                fontsize=10, ha='left')
    
    # Centroid
    yc = rf.centroid_y * 1000
    ax3.plot(0, yc, 'ko', markersize=8, label='Centroid')
    ax3.axhline(y=yc, color='k', linestyle='--', alpha=0.3)
    
    ax3.set_xlim(-50, 150)
    ax3.set_ylim(-20, 180)
    ax3.set_xlabel('Width (mm)')
    ax3.set_ylabel('Height (mm)')
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    # 4. Sliding connection detail
    ax4 = axes[1, 1]
    ax4.set_title('Sliding Connection Detail', fontweight='bold')
    
    conn_data = module.connection_design()
    
    # Draw shell section
    shell_section = Rectangle((0, 0), 100, module.shell_thickness*1000,
                             fill=True, facecolor='blue', alpha=0.3, label='Shell')
    ax4.add_patch(shell_section)
    
    # Draw ring attachment
    ring_attach = Rectangle((30, -20), 40, 25,
                           fill=True, facecolor='red', alpha=0.3, label='Ring Bracket')
    ax4.add_patch(ring_attach)
    
    # Draw slot
    slot = Rectangle((45, -10), conn_data['slot_length_mm'], conn_data['slot_width_mm'],
                    fill=True, facecolor='white', edgecolor='black', linewidth=2)
    ax4.add_patch(slot)
    
    # Draw pin
    pin_x = 45 + conn_data['slot_length_mm']/3  # Pin position in slot
    pin = Circle((pin_x, -10 + conn_data['slot_width_mm']/2), 
                conn_data['slot_width_mm']/2 - 0.5,
                fill=True, facecolor='gray', edgecolor='black')
    ax4.add_patch(pin)
    
    # Expansion arrows
    ax4.arrow(pin_x, -5, conn_data['slot_length_mm']/2, 0,
             head_width=2, head_length=2, fc='green', ec='green', alpha=0.5)
    ax4.arrow(pin_x, -5, -conn_data['slot_length_mm']/3, 0,
             head_width=2, head_length=2, fc='green', ec='green', alpha=0.5)
    
    # Labels
    ax4.text(50, 15, f"Slot: {conn_data['slot_length_mm']:.1f} × {conn_data['slot_width_mm']:.1f} mm",
            fontsize=9)
    ax4.text(50, 10, f"Load: {conn_data['load_per_connection_kN']:.1f} kN",
            fontsize=9)
    ax4.text(50, 5, f"Thermal expansion allowance",
            fontsize=9, style='italic')
    
    ax4.set_xlim(-10, 110)
    ax4.set_ylim(-25, 20)
    ax4.set_xlabel('Length (mm)')
    ax4.set_ylabel('Height (mm)')
    ax4.grid(True, alpha=0.3)
    ax4.legend()
    
    plt.suptitle('Ring-Stiffened Habitat Module Configuration\n2219-T87 Shell + 7050 Ring Frames', 
                fontsize=14, fontweight='bold')
    plt.tight_layout()
    from pathlib import Path

    output_dir = Path.home() / "Documents"
    output_file = output_dir / "ring_study.png"

    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.show()

def optimization_study(shell_thicknesses: List[float], ring_spacings: List[float]):
    """Perform optimization study on shell thickness and ring spacing"""
    results = []
    
    for t_shell in shell_thicknesses:
        for ring_spacing_target in ring_spacings:
            num_rings = int(10.0 / ring_spacing_target) - 1
            
            module = RingStiffenedModule(
                shell_thickness=t_shell,
                num_rings=max(3, num_rings)  # Minimum 3 rings
            )
            
            mass = module.calculate_mass_breakdown()
            ring_stress = module.ring_stress_analysis()
            buckling = module.buckling_analysis_with_rings()
            thermal = module.thermal_expansion_analysis()
            
            results.append({
                'shell_thickness_mm': t_shell * 1000,
                'ring_spacing_m': module.ring_spacing,
                'num_rings': module.num_rings,
                'total_mass_kg': mass['total'],
                'ring_sf_yield': ring_stress['safety_factor_yield'],
                'buckling_sf': buckling['safety_factor_vacuum'],
                'thermal_clearance_mm': thermal['required_clearance_mm'],
                'feasible': (mass['total'] < 10000 and 
                           ring_stress['safety_factor_yield'] > 1.5 and 
                           buckling['safety_factor_vacuum'] > 1.0 and
                           thermal['sliding_joint_feasible'])
            })
    
    # Create optimization plots
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # Extract data for plotting
    feasible_results = [r for r in results if r['feasible']]
    infeasible_results = [r for r in results if not r['feasible']]
    
    # Plot 1: Mass vs configurations
    ax1 = axes[0, 0]
    if feasible_results:
        ax1.scatter([r['shell_thickness_mm'] for r in feasible_results],
                   [r['total_mass_kg'] for r in feasible_results],
                   c='green', s=50, alpha=0.6, label='Feasible')
    if infeasible_results:
        ax1.scatter([r['shell_thickness_mm'] for r in infeasible_results],
                   [r['total_mass_kg'] for r in infeasible_results],
                   c='red', s=50, alpha=0.6, label='Infeasible')
    ax1.set_xlabel('Shell Thickness (mm)')
    ax1.set_ylabel('Total Mass (kg)')
    ax1.set_title('Mass Optimization')
    ax1.axhline(y=10000, color='r', linestyle='--', alpha=0.5, label='Mass limit')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Plot 2: Safety factors
    ax2 = axes[0, 1]
    for r in results:
        color = 'green' if r['feasible'] else 'red'
        ax2.plot([r['shell_thickness_mm'], r['shell_thickness_mm']], 
                [r['ring_sf_yield'], r['buckling_sf']],
                color=color, alpha=0.3)
        ax2.scatter(r['shell_thickness_mm'], r['ring_sf_yield'], 
                   c=color, s=30, alpha=0.6, marker='o')
        ax2.scatter(r['shell_thickness_mm'], r['buckling_sf'], 
                   c=color, s=30, alpha=0.6, marker='s')
    
    ax2.axhline(y=1.5, color='orange', linestyle='--', alpha=0.5, label='Min SF')
    ax2.set_xlabel('Shell Thickness (mm)')
    ax2.set_ylabel('Safety Factor')
    ax2.set_title('Structural Safety Factors')
    ax2.legend(['Ring SF (○)', 'Buckling SF (□)', 'Min Required'])
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Ring spacing effect
    ax3 = axes[1, 0]
    unique_thicknesses = list(set(shell_thicknesses))
    for t in unique_thicknesses[:3]:  # Plot first 3 thicknesses
        data_for_t = [r for r in results if r['shell_thickness_mm'] == t*1000]
        if data_for_t:
            ax3.plot([r['ring_spacing_m'] for r in data_for_t],
                    [r['buckling_sf'] for r in data_for_t],
                    marker='o', label=f'{t*1000:.0f}mm shell')
    
    ax3.set_xlabel('Ring Spacing (m)')
    ax3.set_ylabel('Buckling Safety Factor')
    ax3.set_title('Ring Spacing Optimization')
    ax3.axhline(y=1.5, color='r', linestyle='--', alpha=0.5)
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    # Plot 4: Optimal configurations table
    ax4 = axes[1, 1]
    ax4.axis('tight')
    ax4.axis('off')
    
    # Find best configurations
    if feasible_results:
        sorted_feasible = sorted(feasible_results, key=lambda x: x['total_mass_kg'])[:5]
        
        table_data = []
        for r in sorted_feasible:
            table_data.append([
                f"{r['shell_thickness_mm']:.0f}",
                f"{r['num_rings']}",
                f"{r['ring_spacing_m']:.1f}",
                f"{r['total_mass_kg']:.0f}",
                f"{r['ring_sf_yield']:.1f}",
                f"{r['buckling_sf']:.2f}"
            ])
        
        table = ax4.table(cellText=table_data,
                         colLabels=['Shell\n(mm)', 'Rings', 'Spacing\n(m)', 
                                   'Mass\n(kg)', 'Ring\nSF', 'Buck.\nSF'],
                         cellLoc='center',
                         loc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1.2, 1.5)
        ax4.set_title('Top 5 Optimal Configurations', fontweight='bold', pad=20)
    
    plt.suptitle('Ring-Stiffened Module Optimization Study', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig('/mnt/user-data/outputs/optimization_study.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    return results

def main():
    """Main analysis routine"""
    print("="*70)
    print("RING-STIFFENED HABITAT MODULE ANALYSIS")
    print("NASA Design Challenge TDC-106")
    print("="*70)
    
    # Create module with current design
    module = RingStiffenedModule()
    
    # Mass analysis
    print("\n1. MASS BREAKDOWN")
    print("-"*40)
    mass = module.calculate_mass_breakdown()
    for component, value in mass.items():
        if component != 'total':
            print(f"  {component.capitalize():15s}: {value:7.0f} kg")
    print(f"  {'='*15:15s}  {'='*7:7s}")
    print(f"  {'TOTAL':15s}: {mass['total']:7.0f} kg")
    print(f"  {'Available':15s}: {10000-mass['total']:7.0f} kg")
    
    # Thermal expansion
    print("\n2. THERMAL EXPANSION ANALYSIS")
    print("-"*40)
    thermal = module.thermal_expansion_analysis()
    print(f"  Shell radial expansion:     {thermal['shell_radial_expansion_mm']:6.2f} mm")
    print(f"  Ring radial expansion:      {thermal['ring_radial_expansion_mm']:6.2f} mm")
    print(f"  Differential expansion:     {thermal['differential_expansion_mm']:6.2f} mm")
    print(f"  Required clearance:         {thermal['required_clearance_mm']:6.2f} mm")
    print(f"  Sliding joint feasible:     {'YES ✓' if thermal['sliding_joint_feasible'] else 'NO ✗'}")
    
    # Ring stress analysis
    print("\n3. RING FRAME STRESS ANALYSIS")
    print("-"*40)
    ring = module.ring_stress_analysis()
    print(f"  Max bending moment:         {ring['max_moment_Nm']/1e3:6.1f} kN⋅m")
    print(f"  Direct stress:              {ring['direct_stress_MPa']:6.1f} MPa")
    print(f"  Bending stress:             {ring['bending_stress_MPa']:6.1f} MPa")
    print(f"  Combined stress:            {ring['combined_stress_MPa']:6.1f} MPa")
    print(f"  Safety factor (yield):      {ring['safety_factor_yield']:6.2f}")
    print(f"  Equipment capacity/ring:    {ring['equipment_capacity_kg']:6.0f} kg")
    print(f"  Stress acceptable:          {'YES ✓' if ring['stress_acceptable'] else 'NO ✗'}")
    
    # Buckling analysis
    print("\n4. BUCKLING ANALYSIS")
    print("-"*40)
    buckling = module.buckling_analysis_with_rings()
    print(f"  Critical pressure:          {buckling['critical_pressure_kPa']:6.1f} kPa")
    print(f"  Safety factor (vacuum):     {buckling['safety_factor_vacuum']:6.2f}")
    print(f"  Improvement over plain:     {buckling['improvement_over_unstiffened']:6.1f}x")
    print(f"  Buckling acceptable:        {'YES ✓' if buckling['buckling_acceptable'] else 'NO ✗'}")
    print(f"  Recommendation:             {buckling['recommendation']}")
    
    # Connection design
    print("\n5. SLIDING CONNECTION DESIGN")
    print("-"*40)
    conn = module.connection_design()
    print(f"  Connections per ring:       {conn['connections_per_ring']:6.0f}")
    print(f"  Load per connection:        {conn['load_per_connection_kN']:6.1f} kN")
    print(f"  Pin shear stress:           {conn['pin_shear_stress_MPa']:6.1f} MPa")
    print(f"  Bearing stress:             {conn['bearing_stress_MPa']:6.1f} MPa")
    print(f"  Slot dimensions:            {conn['slot_length_mm']:4.1f} × {conn['slot_width_mm']:3.0f} mm")
    print(f"  Connection type:            {conn['connection_type']}")
    
    # Create visualizations
    print("\n6. GENERATING VISUALIZATIONS...")
    print("-"*40)
    visualize_ring_configuration(module)
    print("  Configuration diagram saved: ring_configuration_visual.png")
    
    # Run optimization study
    print("\n7. OPTIMIZATION STUDY...")
    print("-"*40)
    shell_thicknesses = [0.003, 0.004, 0.005, 0.006]  # meters
    ring_spacings = [1.5, 2.0, 2.5, 3.0]  # meters
    
    results = optimization_study(shell_thicknesses, ring_spacings)
    print("  Optimization plots saved: optimization_study.png")
    
    # Find optimal configuration
    feasible = [r for r in results if r['feasible']]
    if feasible:
        optimal = min(feasible, key=lambda x: x['total_mass_kg'])
        print("\n8. OPTIMAL CONFIGURATION FOUND")
        print("-"*40)
        print(f"  Shell thickness:            {optimal['shell_thickness_mm']:4.0f} mm")
        print(f"  Number of rings:            {optimal['num_rings']:4.0f}")
        print(f"  Ring spacing:               {optimal['ring_spacing_m']:4.1f} m")
        print(f"  Total mass:                 {optimal['total_mass_kg']:4.0f} kg")
        print(f"  Mass savings:               {mass['total']-optimal['total_mass_kg']:4.0f} kg")
    
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)

if __name__ == "__main__":
    main()
