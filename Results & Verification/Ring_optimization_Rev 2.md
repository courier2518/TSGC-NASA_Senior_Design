# Design Note DN-001: Ring Frame Stiffener Selection

**Project:** Artemis Crew Habitat Module  
**Document:** DN-001  
**Revision:** B  
**Date:** 2025-01-30  
**Author:** team Aether 

---

## Revision History

| Rev | Date | Description |
|-----|------|-------------|
| A | 2025-01-30 | Initial release |
| B | 2025-01-30 | Updated to NASA-STD-5001B Table 5 habitable module factors (FOS = 2.0). Revised ring geometry based on re-optimization. Added team simulation validation. |

---

## 1. Purpose

This design note documents the selection and justification of the ring frame stiffening system for the primary pressure vessel structure. The selected configuration provides buckling resistance during launch while accommodating thermal expansion and providing mounting interfaces for internal systems.

---

## 2. Selected Configuration

### 2.1 Ring Frame Design

| Parameter | Value |
|-----------|-------|
| Number of rings | 5 |
| Ring spacing | 1,667 mm |
| Section type | Z-section |
| Web height | 130 mm |
| Web thickness | 1.5 mm |
| Flange thickness | 4.0 mm |
| Outer flange width | 130 mm |
| Inner flange width | 97.5 mm |
| Material | 7050-T7451 Aluminum |

### 2.2 Doubler Plate Design

| Parameter | Value |
|-----------|-------|
| Width (axial) | 80 mm |
| Thickness | 2.0 mm |
| Material | 2219-T87 Aluminum |
| Attachment | Continuous fillet weld to shell interior |
| Slot dimensions | 25 mm × 9 mm (circumferential orientation) |

### 2.3 Frame-to-Doubler Connection

| Parameter | Value |
|-----------|-------|
| Fastener type | Bolted (axial orientation) |
| Fastener size | M8 |
| Fastener material | A286 stainless steel or Ti-6Al-4V |
| Hole type | Slotted (thermal expansion accommodation) |

---

## 3. Applicable Documents and Standards

### 3.1 Primary Standards

| Document | Title | Applicability |
|----------|-------|---------------|
| NASA-STD-5001B w/Change 3 | Structural Design and Test Factors of Safety for Spaceflight Hardware | Factors of safety, verification requirements |
| NASA-SP-8007 | Buckling of Thin-Walled Circular Cylinders | Knockdown factors, buckling analysis methods |
| NASA-STD-6016 | Standard Materials and Processes Requirements for Spacecraft | Material allowables |

### 3.2 Key Requirements from NASA-STD-5001B

This pressure vessel is classified as a **Habitable Module** per NASA-STD-5001B Section 4.2.5.2.1. The following requirements apply:

| Requirement | Section | Value | Compliance |
|-------------|---------|-------|------------|
| [FSR 43] Habitable module factors per Table 5 | 4.2.5.2.1c | Yield: 1.65, Ultimate: 2.0 | ✓ Design uses FOS = 2.0 |
| [FSR 11] Proof pressure test required | 4.1.2.1e | 1.5 × MDP | ✓ Specified in verification plan |
| [FSR 52] Buckling analysis required | 4.5.1 | All items under compression/shear | ✓ Analysis performed |
| [FSR 53] Buckling design loads = ultimate | 4.5.2 | 2.0 × limit load | ✓ Applied |
| [FSR 54] Relieving pressure unfactored | 4.5.3 | Use minimum expected pressure | ✓ 101 kPa used |
| [FSR 55] Buckling evaluation scope | 4.5.4 | General, local, panel, crippling | ✓ All modes evaluated |
| [FSR 56] Knockdown factors for thin shells | 4.5.5 | Per NASA-SP-8007 | ✓ γ = 0.30 applied |
| [FSR 51] Service life factor for fatigue | 4.4 | 4.0 × service life | Pending detailed analysis |

**Table 5 — Minimum Design and Test Factors for Habitable Modules (from NASA-STD-5001B):**

| Pressure Load Case | Yield Design Factor | Ultimate Design Factor | Proof Test Factor |
|--------------------|---------------------|------------------------|-------------------|
| Internal pressure only | 1.65 | 2.0 | 1.5 |
| Negative pressure differential | N/A | 1.5 | N/A |

---

## 4. Design Requirements

### 4.1 Structural Requirements

The ring frame system shall:

1. Prevent shell buckling under ultimate launch loads (FOS = 2.0 per NASA-STD-5001B Table 5)
2. Maintain shell circularity during handling and pressure transients
3. Provide mounting interfaces for internal systems
4. Accommodate thermal expansion across the operational temperature range

### 4.2 Design Loads

| Load Case | Axial | Lateral | Internal Pressure |
|-----------|-------|---------|-------------------|
| Falcon Heavy MECO | 6.0 g | 2.0 g | 101 kPa (1 atm) |
| **Ultimate Design Factor** | **2.0** | **2.0** | — |
| Factored acceleration | 12.0 g | 4.0 g | — |

### 4.3 Thermal Environment

| Condition | Temperature |
|-----------|-------------|
| Minimum (lunar night) | -150°C |
| Maximum (lunar day) | +200°C |
| Total range | 350°C |

### 4.4 Shell Geometry

| Parameter | Value |
|-----------|-------|
| Diameter | 4,250 mm |
| Length | 10,000 mm |
| Wall thickness | 5 mm |
| Material | 2219-T87 Aluminum |
| R/t ratio | 425 |

---

## 5. Trade Study and Optimization

### 5.1 Optimization Approach

A parametric optimization was performed evaluating 91,800 design configurations across the following design space:

| Variable | Range |
|----------|-------|
| Number of rings | 5 to 19 |
| Web height | 80 to 160 mm |
| Web thickness | 1.5 to 5.0 mm |
| Flange thickness | 4.0 to 12.0 mm |
| Doubler thickness | 2.0 to 6.0 mm |

### 5.2 Optimization Criteria

Designs were evaluated against three buckling criteria with NASA habitable module FOS = 2.0:

1. **Global buckling** — classical axial buckling with knockdown factor (γ = 0.30) and pressure stabilization
2. **Panel buckling** — local buckling of shell panels between ring frames with pressure stabilization
3. **Ring stiffness** — minimum moment of inertia to enforce circular cross-section

Feasible designs were ranked by stiffness-to-mass ratio to identify the most structurally efficient configuration.

### 5.3 Results

Of 91,800 configurations evaluated, 85,550 met all structural constraints. The Pareto front identified optimal designs trading mass against stiffness:

| Web Height | Flange Thickness | Stiffening Mass | MS Overall | Stiffness/Mass |
|------------|------------------|-----------------|------------|----------------|
| 130 mm | 4.0 mm | 232 kg | +0.04 | 18,784 mm⁴/kg |
| 140 mm | 4.0 mm | 247 kg | +0.04 | 21,948 mm⁴/kg |
| 150 mm | 4.0 mm | 262 kg | +0.04 | 25,369 mm⁴/kg |
| 160 mm | 4.0 mm | 277 kg | +0.04 | 29,049 mm⁴/kg |

### 5.4 Controlling Constraint

All feasible designs converge to the same global buckling margin (MS = +0.04) because this is controlled by the fundamental shell geometry, material properties, and pressure stabilization — not the ring frames. The ring frames provide secondary benefits (panel buckling, ovalization resistance, mounting) but do not significantly improve global buckling.

### 5.5 Independent Validation

**Team simulation results:** Finite element analysis of the pressurized shell under launch loads without ring stiffeners showed negligible deformation. This confirms that internal pressure (101 kPa) provides substantial stabilization of the shell against buckling, validating the analytical pressure stabilization factors used in the optimization.

---

## 6. Selection Rationale

### 6.1 Selected Design: 130 mm Web Height, 4.0 mm Flange

The minimum mass feasible configuration was selected:

| Parameter | Selected Value |
|-----------|----------------|
| Number of rings | 5 |
| Web height | 130 mm |
| Flange thickness | 4.0 mm |
| Stiffening mass | 232 kg |
| Overall margin | +0.04 |

### 6.2 Rationale

#### 6.2.1 Margin Adequacy

The +4% margin on global buckling is acceptable based on:

1. **Team simulation validation** — independent FEA confirms negligible deformation under pressurized load
2. **Conservative knockdown factor** — γ = 0.30 per NASA-SP-8007 is conservative for well-manufactured aerospace structures
3. **Pressure stabilization** — 101 kPa internal pressure provides 51% increase in buckling resistance
4. **Prototype testing required** — per NASA-STD-5001B, habitable modules require proof pressure testing which will validate the design

#### 6.2.2 Secondary Margins

The selected design provides comfortable margins on secondary failure modes:

| Failure Mode | Margin of Safety |
|--------------|------------------|
| Panel buckling | +0.98 (98%) |
| Ring stiffness | +0.16 (16%) |

#### 6.2.3 Mass Efficiency

The selected design achieves minimum stiffening mass (232 kg) while meeting all NASA requirements. Heavier configurations do not improve the controlling global buckling margin.

#### 6.2.4 Design Philosophy Alignment

The project design philosophy is: *"If the problem is geometry, we solve it with geometry."*

The selected configuration embodies this philosophy:

- Buckling is prevented through geometric stiffening and pressure stabilization
- Tall, thin Z-sections (130 mm web, 1.5 mm thickness) maximize geometric efficiency
- Slotted connections solve thermal expansion geometrically
- Ring frames provide mounting interfaces without penetrating pressure boundary

---

## 7. Structural Performance

### 7.1 Section Properties

| Property | Value |
|----------|-------|
| Cross-sectional area | 1,105 mm² |
| Moment of inertia | 4.36 × 10⁶ mm⁴ |
| Required moment of inertia | 3.76 × 10⁶ mm⁴ |
| Section efficiency | 116% of requirement |

### 7.2 Stress Analysis

| Parameter | Value |
|-----------|-------|
| Applied stress (with FOS = 2.0) | 45.3 MPa |
| Global buckling allowable | 47.2 MPa |
| Panel buckling allowable | 89.8 MPa |
| Pressure stabilization factor | 1.51× |
| Knockdown factor (γ) | 0.30 |

### 7.3 Margins of Safety

| Failure Mode | Margin of Safety | Status |
|--------------|------------------|--------|
| Global buckling | +0.04 | ✓ Positive |
| Panel buckling | +0.98 | ✓ Positive |
| Ring stiffness | +0.16 | ✓ Positive |
| **Overall** | **+0.04** | **✓ Positive** |

All margins are positive. The controlling case is global shell buckling, which is the fundamental stability mode for a thin-walled pressure vessel.

---

## 8. Mass Summary

### 8.1 Stiffening System

| Component | Quantity | Unit Mass | Total Mass |
|-----------|----------|-----------|------------|
| Z-section rings | 5 | 40.4 kg | 202 kg |
| Doubler plates | 5 rings | 6.1 kg/ring | 30 kg |
| Fasteners (est.) | ~150 | 0.05 kg | 8 kg |
| **Stiffening total** | | | **240 kg** |

### 8.2 Primary Structure

| Component | Mass |
|-----------|------|
| Pressure shell (cylinder) | 1,896 kg |
| Stiffening system | 240 kg |
| **Cylinder subtotal** | **2,136 kg** |

### 8.3 Mass Budget Impact

| Allocation | Mass | % of Budget |
|------------|------|-------------|
| Total vehicle budget | 10,000 kg | 100% |
| Cylinder structure | 2,136 kg | 21.4% |
| Remaining for domes, thermal, systems | 7,864 kg | 78.6% |

---

## 9. Thermal Expansion Accommodation

### 9.1 Radial Expansion

Shell radius change over temperature range:

$$\Delta R = R \cdot \alpha \cdot \Delta T = 2125 \times 22.5 \times 10^{-6} \times 350 = 16.7 \text{ mm}$$

From assembly temperature (20°C) to extremes:
- Cold case (-150°C): -8.1 mm (contraction)
- Hot case (+200°C): +8.6 mm (expansion)

### 9.2 Slot Sizing

| Parameter | Value |
|-----------|-------|
| Required travel | ±8.6 mm |
| Tolerance allowance | ±3 mm |
| Slot length | 25 mm |
| Slot width | 9 mm (M8 clearance) |

Slots are oriented circumferentially to permit radial shell movement without binding.

### 9.3 CTE Compatibility

| Material | CTE (×10⁻⁶/°C) |
|----------|----------------|
| 2219 shell | 22.5 |
| 2219 doubler | 22.5 |
| 7050 ring | 23.5 |

The 4% CTE mismatch between ring and doubler produces negligible stress due to the slotted connection.

---

## 10. Interface Definition

### 10.1 Mounting Surface

The outer flange of each Z-ring provides the mounting interface for internal systems:

| Parameter | Specification |
|-----------|---------------|
| Available width | 130 mm |
| Usable width (less edge distance) | 110 mm |
| Hole pattern | M6 tapped, 50 mm pitch |
| Surface finish | As-machined or anodized |

### 10.2 Allowable Loads

Preliminary allowable loads per ring (to be verified by detailed analysis):

| Load Type | Allowable |
|-----------|-----------|
| Distributed radial | 500 N/m |
| Point load (at fastener) | 2,000 N |
| Moment (per fastener group) | 500 N·m |

Systems teams shall coordinate mounting requirements with structures to verify adequacy.

### 10.3 Keep-Out Zones

The following areas are not available for system mounting:

- Within 50 mm of ring splice joints
- Doubler plate surface (reserved for ring attachment)
- End dome transition regions (separate interface definition)

---

## 11. Verification Plan

### 11.1 Analysis

| Item | Method | Standard |
|------|--------|----------|
| Global buckling | Linear eigenvalue FEA | NASA-SP-8007 |
| Nonlinear buckling | Geometric nonlinear FEA with imperfections | NASA-STD-5001B 4.5.5 |
| Ring stiffness | Hand calculation verified by FEA | — |
| Thermal stress | Coupled thermal-structural FEA | — |
| Fatigue life | Cycle counting with life factor = 4.0 | NASA-STD-5001B 4.4 |

### 11.2 Test

| Item | Method | Requirement |
|------|--------|-------------|
| Proof pressure test | 1.5 × MDP (152 kPa) | NASA-STD-5001B [FSR 11] |
| Workmanship verification | Per approved QA plan | NASA-STD-5001B [FSR 25] |
| Ring section properties | Coupon testing of formed sections | — |
| Bolted joint strength | Joint pull test | — |
| Thermal cycling | Subassembly thermal vacuum test | — |

### 11.3 Proof Test Requirement

Per NASA-STD-5001B Table 5, each habitable module flight article shall be proof pressure tested at:

$$P_{proof} = 1.5 \times MDP = 1.5 \times 101 = 152 \text{ kPa}$$

The structure shall show no evidence of detrimental yielding after proof test.

---

## 12. Compliance Matrix

| NASA-STD-5001B Requirement | Section | Status | Notes |
|----------------------------|---------|--------|-------|
| [FSR 43] Habitable module FOS per Table 5 | 4.2.5.2.1c | ✓ Compliant | Ultimate FOS = 2.0 applied |
| [FSR 11] Proof pressure test | 4.1.2.1e | ✓ Planned | 152 kPa proof test specified |
| [FSR 52] Buckling analysis | 4.5.1 | ✓ Compliant | Global, panel, ring modes analyzed |
| [FSR 53] Ultimate loads for buckling | 4.5.2 | ✓ Compliant | 2.0 × limit load used |
| [FSR 54] Unfactored relieving pressure | 4.5.3 | ✓ Compliant | 101 kPa internal pressure |
| [FSR 55] Buckling evaluation scope | 4.5.4 | ✓ Compliant | All modes addressed |
| [FSR 56] Shell knockdown factors | 4.5.5 | ✓ Compliant | γ = 0.30 per SP-8007 |
| [FSR 51] Fatigue life factor | 4.4 | Pending | 4.0× life factor to be applied |
| [FSR 41] Dimensional stability | 4.2.5.2.1a | ✓ Compliant | Thermal expansion accommodated |

---

## 13. Open Items

| Item | Description | Owner | Due |
|------|-------------|-------|-----|
| 1 | Detail ring splice joint design | Structures | TBD |
| 2 | Finalize doubler segment layout | Structures | TBD |
| 3 | Coordinate system mounting loads | Systems | TBD |
| 4 | End ring interface to domes | Structures | TBD |
| 5 | Complete nonlinear buckling FEA | Structures | TBD |
| 6 | Fatigue analysis with 4.0× life factor | Structures | TBD |
| 7 | Proof test procedure development | Test | TBD |

---

## 14. References

1. NASA-STD-5001B w/Change 3, "Structural Design and Test Factors of Safety for Spaceflight Hardware," 2022
2. NASA-SP-8007, "Buckling of Thin-Walled Circular Cylinders," 1968
3. NASA-STD-6016, "Standard Materials and Processes Requirements for Spacecraft"
4. MMPDS-17, "Metallic Materials Properties Development and Standardization"
5. Project Ring Frame Optimization Script, `ring_optimizer.py`, Rev B
6. Project optimization results, `optimal_designs.csv`
7. Team pressurized shell FEA simulation (internal validation)

---

## 15. Approval

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Author | Brandon Portillo | BP |01-30-2026 |
| Checker | | | |
| Project Manager | | | |

---

*End of Document*