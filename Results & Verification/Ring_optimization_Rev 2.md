# Design Note DN-001: Ring Frame Stiffener Selection

**Project:** Artemis Crew Habitat Module  
**Document:** DN-001  
**Revision:** A  
**Date:** 2025-01-30  
**Author:** Structures Team  

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
| Web height | 120 mm |
| Web thickness | 1.5 mm |
| Flange thickness | 6.0 mm |
| Outer flange width | 120 mm |
| Inner flange width | 90 mm |
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

## 3. Design Requirements

### 3.1 Structural Requirements

The ring frame system shall:

1. Prevent shell buckling under launch loads (6g axial, 2g lateral combined)
2. Maintain shell circularity during handling and pressure transients
3. Provide mounting interfaces for internal systems
4. Accommodate thermal expansion across the operational temperature range

### 3.2 Design Loads

| Load Case | Axial | Lateral | Internal Pressure |
|-----------|-------|---------|-------------------|
| Falcon Heavy MECO | 6.0 g | 2.0 g | 101 kPa (1 atm) |
| Factor of Safety | 1.4 | 1.4 | — |

### 3.3 Thermal Environment

| Condition | Temperature |
|-----------|-------------|
| Minimum (lunar night) | -150°C |
| Maximum (lunar day) | +200°C |
| Total range | 350°C |

### 3.4 Shell Geometry

| Parameter | Value |
|-----------|-------|
| Diameter | 4,250 mm |
| Length | 10,000 mm |
| Wall thickness | 5 mm |
| Material | 2219-T87 Aluminum |
| R/t ratio | 425 |

---

## 4. Trade Study Summary

### 4.1 Optimization Approach

A parametric optimization was performed evaluating 75,000 design configurations across the following design space:

| Variable | Range |
|----------|-------|
| Number of rings | 5 to 19 |
| Web height | 30 to 120 mm |
| Web thickness | 1.5 to 6.0 mm |
| Flange thickness | 1.5 to 6.0 mm |
| Doubler thickness | 2.0 to 6.0 mm |

### 4.2 Optimization Criteria

Designs were evaluated against three buckling criteria:

1. **Global buckling** — classical axial buckling with knockdown factor and pressure stabilization
2. **Panel buckling** — local buckling of shell panels between ring frames
3. **Ring stiffness** — minimum moment of inertia to enforce circular cross-section

Feasible designs were ranked by stiffness-to-mass ratio to identify the most structurally efficient configuration.

### 4.3 Results

Of 75,000 configurations evaluated, 19,980 met all structural constraints. The Pareto front identified four optimal designs trading mass against stiffness margin:

| Flange Thickness | Stiffening Mass | Margin of Safety | Stiffness/Mass |
|------------------|-----------------|------------------|----------------|
| 4.5 mm | 236 kg | +0.03 | 16,417 mm⁴/kg |
| 5.0 mm | 256 kg | +0.15 | 16,905 mm⁴/kg |
| 5.5 mm | 275 kg | +0.27 | 17,348 mm⁴/kg |
| 6.0 mm | 294 kg | +0.39 | 17,758 mm⁴/kg |

### 4.4 Key Finding

The optimizer consistently selected configurations with:

- **Fewer rings (5)** rather than many rings
- **Taller webs (120 mm)** rather than shorter webs
- **Thin web material (1.5 mm)** with thicker flanges

This result reflects the cubic relationship between section height and moment of inertia. Doubling the web height increases stiffness by approximately 8× while only doubling the material. Fewer, taller rings are more mass-efficient than many smaller rings.

---

## 5. Selection Rationale

### 5.1 Selected Design: 6.0 mm Flange Thickness

The 6.0 mm flange configuration was selected over the minimum mass (4.5 mm) configuration for the following reasons:

#### 5.1.1 Margin Adequacy

| Design | Overall Margin |
|--------|----------------|
| 4.5 mm flange | +0.03 (3%) |
| 6.0 mm flange | +0.39 (39%) |

The minimum mass design provides only 3% margin against the ring stiffness requirement. This leaves no room for:

- Manufacturing tolerances
- Material property scatter
- Analysis uncertainty
- Future mass growth of internal systems

The selected design provides 39% margin, which is appropriate for a crewed spacecraft in a senior design context where detailed analysis refinement may not occur.

#### 5.1.2 Mass Impact

The mass penalty for the additional margin is modest:

| Component | 4.5 mm Design | 6.0 mm Design | Delta |
|-----------|---------------|---------------|-------|
| Ring frames | 206 kg | 264 kg | +58 kg |
| Doublers | 30 kg | 30 kg | 0 kg |
| **Total stiffening** | **236 kg** | **294 kg** | **+58 kg** |

An additional 58 kg represents 0.6% of the 10,000 kg mass budget — a negligible penalty for substantially improved structural confidence.

#### 5.1.3 Fabrication Considerations

Thicker flanges (6.0 mm vs 4.5 mm) provide:

- Greater bearing area for bolted connections
- Increased resistance to local flange buckling during handling
- More material for tapped mounting holes
- Reduced sensitivity to edge damage

#### 5.1.4 Design Philosophy Alignment

The project design philosophy is: *"If the problem is geometry, we solve it with geometry."*

The selected configuration embodies this philosophy:

- Buckling is prevented through geometric stiffening, not material mass
- Tall, thin Z-sections maximize geometric efficiency
- Slotted connections solve thermal expansion geometrically rather than through complex analysis or exotic materials

---

## 6. Structural Performance

### 6.1 Section Properties

| Property | Value |
|----------|-------|
| Cross-sectional area | 1,440 mm² |
| Moment of inertia | 5.22 × 10⁶ mm⁴ |
| Required moment of inertia | 3.76 × 10⁶ mm⁴ |
| Section efficiency | 139% of requirement |

### 6.2 Stress Analysis

| Parameter | Value |
|-----------|-------|
| Applied stress (with FOS) | 31.7 MPa |
| Global buckling allowable | 47.2 MPa |
| Panel buckling allowable | 44.9 MPa |
| Pressure stabilization factor | 1.51× |

### 6.3 Margins of Safety

| Failure Mode | Margin of Safety |
|--------------|------------------|
| Global buckling | +0.49 |
| Panel buckling | +0.42 |
| Ring stiffness | +0.39 |
| **Overall** | **+0.39** |

All margins are positive with the controlling case being ring stiffness.

---

## 7. Mass Summary

### 7.1 Stiffening System

| Component | Quantity | Unit Mass | Total Mass |
|-----------|----------|-----------|------------|
| Z-section rings | 5 | 52.8 kg | 264 kg |
| Doubler plates | 5 rings | 6.1 kg/ring | 30 kg |
| Fasteners (est.) | ~200 | 0.05 kg | 10 kg |
| **Stiffening total** | | | **304 kg** |

### 7.2 Primary Structure

| Component | Mass |
|-----------|------|
| Pressure shell (cylinder) | 1,896 kg |
| Stiffening system | 304 kg |
| **Cylinder subtotal** | **2,200 kg** |

### 7.3 Mass Budget Impact

| Allocation | Mass | % of Budget |
|------------|------|-------------|
| Total vehicle budget | 10,000 kg | 100% |
| Cylinder structure | 2,200 kg | 22% |
| Remaining for domes, thermal, systems | 7,800 kg | 78% |

---

## 8. Thermal Expansion Accommodation

### 8.1 Radial Expansion

Shell radius change over temperature range:

$$\Delta R = R \cdot \alpha \cdot \Delta T = 2125 \times 22.5 \times 10^{-6} \times 350 = 16.7 \text{ mm}$$

From assembly temperature (20°C) to extremes:
- Cold case (-150°C): -8.1 mm (contraction)
- Hot case (+200°C): +8.6 mm (expansion)

### 8.2 Slot Sizing

| Parameter | Value |
|-----------|-------|
| Required travel | ±8.6 mm |
| Tolerance allowance | ±3 mm |
| Slot length | 25 mm |
| Slot width | 9 mm (M8 clearance) |

Slots are oriented circumferentially to permit radial shell movement without binding.

### 8.3 CTE Compatibility

| Material | CTE (×10⁻⁶/°C) |
|----------|----------------|
| 2219 shell | 22.5 |
| 2219 doubler | 22.5 |
| 7050 ring | 23.5 |

The 4% CTE mismatch between ring and doubler produces negligible stress due to the slotted connection.

---

## 9. Interface Definition

### 9.1 Mounting Surface

The outer flange of each Z-ring provides the mounting interface for internal systems:

| Parameter | Specification |
|-----------|---------------|
| Available width | 120 mm |
| Usable width (less edge distance) | 100 mm |
| Hole pattern | M6 tapped, 50 mm pitch |
| Surface finish | As-machined or anodized |

### 9.2 Allowable Loads

Preliminary allowable loads per ring (to be verified by detailed analysis):

| Load Type | Allowable |
|-----------|-----------|
| Distributed radial | 500 N/m |
| Point load (at fastener) | 2,000 N |
| Moment (per fastener group) | 500 N·m |

Systems teams shall coordinate mounting requirements with structures to verify adequacy.

### 9.3 Keep-Out Zones

The following areas are not available for system mounting:

- Within 50 mm of ring splice joints
- Doubler plate surface (reserved for ring attachment)
- End dome transition regions (separate interface definition)

---

## 10. Verification Plan

### 10.1 Analysis

| Item | Method |
|------|--------|
| Global buckling | Linear eigenvalue FEA |
| Nonlinear buckling | Geometric nonlinear FEA with imperfections |
| Ring stiffness | Hand calculation verified by FEA |
| Thermal stress | Coupled thermal-structural FEA |

### 10.2 Test

| Item | Method |
|------|--------|
| Ring section properties | Coupon testing of formed sections |
| Bolted joint strength | Joint pull test |
| Thermal cycling | Subassembly thermal vacuum test |

---

## 11. Open Items

| Item | Description | Owner | Due |
|------|-------------|-------|-----|
| 1 | Detail ring splice joint design | Structures | TBD |
| 2 | Finalize doubler segment layout | Structures | TBD |
| 3 | Coordinate system mounting loads | Systems | TBD |
| 4 | End ring interface to domes | Structures | TBD |
| 5 | Complete FEA model | Structures | TBD |

---

## 12. References

1. NASA SP-8007, "Buckling of Thin-Walled Circular Cylinders," 1968
2. NASA-STD-5001, "Structural Design and Test Factors of Safety for Spaceflight Hardware"
3. MMPDS-17, "Metallic Materials Properties Development and Standardization"
4. Project Ring Frame Optimization Script, `ring_optimizer.py`
5. Project optimization results, `optimal_designs.csv`

---

## 13. Approval

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Author | | | |
| Checker | | | |
| Structures Lead | | | |
| Project Manager | | | |

---

*End of Document*
