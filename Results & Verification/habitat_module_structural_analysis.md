# Structural Analysis - Lunar/Mars Habitat Module
## NASA Design Challenge TDC-106

### Module Specifications
- **Configuration**: Horizontal cylindrical pressure vessel
- **Outer Diameter**: 4.25 m
- **Wall Thickness**: 5 mm
- **Length**: 10 m
- **Material**: 2219-T87 Aluminum Alloy
- **Support**: Leg-supported structure

---

## Material Properties - 2219-T87 Aluminum

| Property | Value | Units |
|----------|-------|-------|
| Yield Strength (Fty) | 395 | MPa |
| Ultimate Strength (Ftu) | 475 | MPa |
| Elastic Modulus (E) | 73.8 | GPa |
| Poisson's Ratio (ν) | 0.33 | - |
| Density (ρ) | 2,840 | kg/m³ |
| CTE (α) | 22.3 × 10⁻⁶ | /°C |
| Fracture Toughness (KIC) | 25-35 | MPa√m |

**Note**: 2219-T87 is an excellent choice for space applications - high strength-to-weight ratio and proven heritage (Space Shuttle External Tank, Ares I).

---

## Critical Load Cases Analysis

### 1. Internal Pressure Loads (Primary Design Driver)

**Hoop Stress (Circumferential)**:
```
σ_hoop = (P × r) / t
σ_hoop = (101,325 Pa × 2.125 m) / 0.005 m
σ_hoop = 43.06 MPa
```

**Longitudinal Stress**:
```
σ_long = (P × r) / (2t)
σ_long = (101,325 Pa × 2.125 m) / (2 × 0.005 m)
σ_long = 21.53 MPa
```

**Safety Margins**:
- Yield Margin: 395 MPa / 43.06 MPa = 9.17 (Requirement: 2.5)
- Ultimate Margin: 475 MPa / 43.06 MPa = 11.03 (Requirement: 4.0)
- **Status**: ✅ Exceeds NASA pressure vessel requirements

### 2. Module Mass Calculations

**Cylinder Shell Mass**:
```
Volume = π × [(R_outer)² - (R_inner)²] × L
Volume = π × [(2.125)² - (2.120)²] × 10
Volume = 0.333 m³
Mass_shell = 0.333 m³ × 2,840 kg/m³ = 946 kg
```

**End Caps (2x hemispherical assumed)**:
```
Mass_endcaps ≈ 200 kg (estimated)
```

**Total Structural Mass**: ~1,150 kg (leaving ~8,850 kg for systems, legs, equipment)

### 3. Launch Loads

**Axial Load (6g worst case)**:
```
F_axial = 6 × 9.81 × 10,000 kg = 588.6 kN
```

**Distributed over cylinder**:
```
σ_axial = F / A_cross-section
A = π × (2.125² - 2.120²) × 10⁶ mm²
σ_axial = 588,600 N / 66,600 mm² = 8.84 MPa
```

**Combined Launch Stress (von Mises)**:
```
σ_vm = √(σ_hoop² + σ_long² + σ_axial² - σ_hoop×σ_long - σ_long×σ_axial - σ_hoop×σ_axial)
σ_vm ≈ 45 MPa (conservative estimate)
```

### 4. Thermal Stress Analysis

**Lunar Temperature Range**: -173°C to +127°C (ΔT = 300°C)

**Thermal Stress (if fully constrained)**:
```
σ_thermal = E × α × ΔT
σ_thermal = 73.8 GPa × 22.3×10⁻⁶ × 300
σ_thermal = 494 MPa (if fully constrained)
```

**Critical Finding**: ⚠️ Thermal expansion joints or flexible mounting required!

### 5. Buckling Analysis

**Critical Buckling Pressure (External)**:
```
P_cr = (2.42 × E × (t/D)^2.5) / √(1 - ν²)
P_cr = (2.42 × 73.8×10⁹ × (0.005/4.25)^2.5) / √(1 - 0.33²)
P_cr ≈ 8,400 Pa
```

**Buckling Safety Factor**:
- Mars atmosphere (600 Pa): SF = 14 ✅
- Depressurization event: Requires internal stiffeners

### 6. Leg Support Analysis

**Assumptions**:
- 4 or 6 support legs
- Must handle launch, landing, and operational loads

**Load per Leg (4-leg config)**:
```
Launch (6g): 147 kN per leg
Lunar operation: 4 kN per leg
Mars operation: 9.3 kN per leg
```

**Critical Considerations**:
- Stress concentration at leg attachment points
- Need doubler plates or reinforcement rings
- Moment loads from thermal expansion

---

## FEA Model Recommendations

### Element Types
- **Shell**: Use SHELL181 (4-node) or SHELL281 (8-node) elements
- **Legs**: BEAM188 elements with appropriate cross-sections
- **Joints**: Consider contact elements for leg interfaces

### Mesh Sizing
- Global element size: 50-100 mm
- Refinement at:
  - Leg attachment points (10-20 mm)
  - Airlock/port openings
  - End cap transitions

### Boundary Conditions
1. **Launch Configuration**:
   - Fixed at launch vehicle interface points
   - Apply acceleration loads as body forces

2. **Operational Configuration**:
   - Fixed or pinned at leg base points
   - Internal pressure: 101.3 kPa
   - External: vacuum or Mars atmosphere
   - Temperature field for thermal analysis

### Load Steps for Analysis
1. **Step 1**: Apply gravity (Earth, Moon, or Mars)
2. **Step 2**: Apply internal pressure
3. **Step 3**: Apply thermal loads
4. **Step 4**: Apply live loads/equipment masses
5. **Step 5**: For fatigue - cycle pressure loads

---

## Design Optimization Recommendations

### Wall Thickness Concerns
**Issue**: 5mm thickness provides high safety margins but may be inefficient

**Recommendations**:
1. **Variable Thickness**: 
   - Reduce to 3-4mm in low-stress regions
   - Maintain 5-6mm at leg attachments
   
2. **Stiffening Strategy**:
   - Add longitudinal stiffeners (T or I-sections)
   - Circumferential rings at 2-3m spacing
   - This prevents buckling while reducing mass

### Leg Attachment Design
```
Recommended Features:
- Doubler plate: 10-15mm thickness
- Spread load over 0.5m × 0.5m area
- Use multiple fasteners or welded connection
- Include spherical bearings for thermal expansion
```

### Thermal Management
1. **Multi-Layer Insulation (MLI)**: External blankets
2. **Thermal break**: Between legs and cylinder
3. **Radiator panels**: For heat rejection
4. **Phase change materials**: For thermal mass

---

## Critical Design Verification Tests

### Phase 2 Analysis Requirements
1. **Linear Static FEA**:
   - All load cases individually
   - Combined worst-case scenarios
   - Safety factor verification

2. **Eigenvalue Buckling**:
   - Determine critical buckling modes
   - Verify against external pressure scenarios

3. **Modal Analysis**:
   - Natural frequencies (avoid launch vehicle resonance)
   - Target: First mode > 25 Hz

4. **Thermal-Structural**:
   - Steady-state thermal distribution
   - Resulting thermal stresses
   - Day/night cycling effects

5. **Fatigue Assessment**:
   - Pressure cycling (10,000 cycles minimum)
   - Thermal cycling (mission duration)
   - Stress concentration factors at joints

---

## Mass Budget Tracking

| Component | Mass (kg) | Notes |
|-----------|-----------|-------|
| Cylinder Shell | 946 | 5mm Al 2219-T87 |
| End Caps | 200 | Estimated hemispherical |
| Stiffeners/Rings | 300 | If added for buckling |
| Leg Structure | 400 | 4-6 legs with joints |
| Airlock/Ports | 500 | One primary, one emergency |
| MLI/Thermal | 150 | External insulation |
| **Subtotal Structure** | 2,496 | |
| **Remaining for Systems** | 7,504 | ECLSS, power, interior |
| **Total** | 10,000 | Within limit ✅ |

---

## Next Steps for Your Team

### Immediate Actions:
1. **Refine Geometry**:
   - Confirm end cap design (hemispherical vs. torispherical)
   - Determine exact leg positions and quantity
   - Locate airlock and utility ports

2. **Initial FEA**:
   - Start with simplified pressure + gravity case
   - Verify mesh convergence
   - Check stress concentrations

3. **Trade Studies**:
   - Wall thickness optimization (3mm vs. 5mm with stiffeners)
   - 4 legs vs. 6 legs configuration
   - Aluminum 2219-T87 vs. Al-Li alloys for mass savings

### Documentation for Phase 2 Submission:
- [ ] FEA model description and mesh details
- [ ] Load case matrix with safety factors
- [ ] Stress/displacement contour plots
- [ ] Mass breakdown with contingency
- [ ] Thermal analysis results
- [ ] Modal analysis (first 5 modes minimum)

---

## Reference Standards
- NASA-STD-5001: Structural Design Requirements
- NASA-STD-5012: Strength and Life Assessment
- NASA-HDBK-5010: Fracture Control Implementation
- AIAA S-080: Space Systems Metallic Pressure Vessels
- AIAA S-081: Space Systems Composite Pressure Vessels

---

*Analysis prepared for NASA Design Challenge TDC-106*
*Contact: Robert Nuckols (robert.s.nuckols@nasa.gov)*