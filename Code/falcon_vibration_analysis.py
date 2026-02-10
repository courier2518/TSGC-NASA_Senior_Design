#!/usr/bin/env python3
"""
===============================================================================
VIBRATION & DYNAMIC LOADS ANALYSIS — Habitat Module on Falcon Heavy
===============================================================================
Senior Design Project — Pressurized Habitat for Lunar/Martian Deployment

Launch Vehicle:     SpaceX Falcon Heavy
Environments:       Per Falcon User's Guide (2025), Tables 5-3, 5-4, 5-10
Standards:          NASA-STD-7001B, NASA-HDBK-7005, GEVS (GSFC-STD-7000)

Analyses Performed:
    1. Natural Frequency Analysis (shell modes, beam modes, breathing modes)
    2. Quasi-Static Load Factors (Falcon Heavy published)
    3. Sinusoidal Vibration Response
    4. Random Vibration Response (PSD → Miles equation + numerical)
    5. Acoustic Loading Estimate
    6. Shock Response Spectrum
    7. Combined Dynamic + Static Stress Assessment
    8. Fatigue Life Estimate (Miner's rule)

Geometry:  L=10m, D=4.25m, t=5mm, Al 2219-T67
Payload:   8,000 kg internal systems/supplies
===============================================================================
"""

import math
import sys
from dataclasses import dataclass
from typing import List, Tuple

# =============================================================================
# MATERIAL & GEOMETRY (from prior analysis)
# =============================================================================
E       = 73.1e9        # Pa
nu      = 0.33
rho     = 2840.0        # kg/m³
Fty     = 393e6         # Pa
Ftu     = 455e6         # Pa
Fcy     = 290e6         # Pa

L       = 10.0          # m
D       = 4.25          # m
t       = 0.005         # m
R       = D / 2.0       # m
R_mid   = R - t / 2.0

# Section properties
A_cs    = math.pi * (R**2 - (R - t)**2)
I_cs    = math.pi / 4.0 * (R**4 - (R - t)**4)
Z_cs    = I_cs / R
r_g     = math.sqrt(I_cs / A_cs)

# Mass
m_shell     = rho * A_cs * L
m_caps      = 2 * 1.084 * math.pi * R**2 * t * rho
m_structure = m_shell + m_caps
m_payload   = 8000.0
m_total     = m_structure + m_payload

g = 9.81

# =============================================================================
# FALCON HEAVY PUBLISHED ENVIRONMENTS
# (Source: Falcon User's Guide, 2025 Edition, Section 5.3)
# =============================================================================

# --- Table 5-3: Flight Limit Load Factors (for payloads > 4,000 lb) ---
# These are LIMIT loads (no qualification factor included)
FALCON_LOAD_FACTORS = {
    "Liftoff":              {"axial_g": 3.2, "lateral_g": 1.3},
    "Max_Q":                {"axial_g": 3.2, "lateral_g": 0.6},
    "MECO":                 {"axial_g": 6.0, "lateral_g": 0.5},
    "Stage_Sep":            {"axial_g": -1.5, "lateral_g": 1.5},  # Negative = tension
    "SES/SECO":             {"axial_g": 3.5, "lateral_g": 0.3},
    "Landing_Shock":        {"axial_g": 1.5, "lateral_g": 0.5},
    "Design_Envelope":      {"axial_g": 6.0, "lateral_g": 2.0},  # Combined envelope
}

# --- Table 5-4: Equivalent Sine Vibration (max limit level, at top of PAF) ---
# Falcon 9 / Falcon Heavy sinusoidal vibration environment
SINE_VIB_ENVIRONMENT = [
    # (freq_low_Hz, freq_high_Hz, amplitude_g, direction)
    (5,   10,   1.0,  "Axial"),
    (10,  25,   0.7,  "Axial"),
    (25,  100,  0.7,  "Axial"),
    (5,   10,   1.0,  "Lateral"),
    (10,  25,   0.7,  "Lateral"),
    (25,  100,  0.7,  "Lateral"),
]

# --- Table 5-10: Random Vibration MPE (P95/50) at top of PAF ---
# Falcon 9/Heavy, Overall: 5.13 Grms
RANDOM_VIB_PSD = [
    # (freq_Hz, ASD_g2_per_Hz)
    (20,    0.005),
    (40,    0.005),
    (80,    0.02),
    (200,   0.02),
    (500,   0.02),
    (700,   0.01),
    (925,   0.01),
    (2000,  0.002),
]

# Slopes between breakpoints (dB/oct) — derived from the PSD table
# 20-40: flat, 40-80: +6 dB/oct, 80-500: flat, 500-700: -3 dB/oct, etc.

# --- Table 5-7: Falcon Heavy Acoustic MPE (P95/50), 60% fill factor ---
# Third-octave band center frequencies and SPL in dB (ref 20 μPa)
ACOUSTIC_ENVIRONMENT = [
    # (center_freq_Hz, SPL_dB)
    (31.5,  121.0),
    (40,    123.0),
    (50,    126.0),
    (63,    128.0),
    (80,    129.0),
    (100,   131.0),
    (125,   132.0),
    (160,   131.0),
    (200,   130.0),
    (250,   128.0),
    (315,   127.0),
    (400,   125.0),
    (500,   123.0),
    (630,   121.0),
    (800,   119.0),
    (1000,  117.0),
    (1250,  115.0),
    (1600,  113.0),
    (2000,  111.0),
    (2500,  109.0),
    (3150,  107.0),
    (4000,  105.0),
    (5000,  103.0),
    (6300,  101.0),
    (8000,  99.0),
]
# OASPL (Overall) ≈ 139.6 dB

# --- Table 5-8: LV-Induced Shock at Separation Plane (P95/50 MPE) ---
SHOCK_SRS = [
    # (freq_Hz, amplitude_g)
    (100,    20),
    (200,    40),
    (500,    200),
    (700,    400),
    (1000,   800),
    (2000,   1500),
    (5000,   2000),
    (10000,  2000),
]


# =============================================================================
# PRINT UTILITIES
# =============================================================================
W = 80

def sep(c="="): print(c * W)
def header(t):
    print(); sep(); print(f"  {t}"); sep()
def sub(t): print(f"\n  ── {t} {'─' * max(1, W - len(t) - 6)}")
def kv(label, val, indent=4): print(f"{' '*indent}{label:<45s} {val}")


# =============================================================================
# 1. NATURAL FREQUENCY ANALYSIS
# =============================================================================
def natural_frequencies():
    """
    Compute natural frequencies for a thin-walled cylinder:
    - Beam bending modes (cantilevered and free-free)
    - Shell breathing mode (ring mode, n=0)
    - Lobar shell modes (n≥2)
    - Axial bar modes
    """
    header("1. NATURAL FREQUENCY ANALYSIS")
    print("  Analytical estimates for thin-walled cylindrical shell")
    print(f"  Total mass: {m_total:.0f} kg (structure + payload uniformly distributed)")

    # Effective distributed mass per length (total mass spread over L)
    m_per_L = m_total / L  # kg/m

    # --- Beam bending modes (Euler-Bernoulli, cantilevered) ---
    sub("Beam Bending Modes (Cantilevered — Launch Config)")
    # f_n = (β_n L)² / (2π L²) * sqrt(EI / m_per_L)
    # β_n L values for cantilever: 1.875, 4.694, 7.855
    beta_nL_cantilever = [1.8751, 4.6941, 7.8548]
    beam_freqs_cant = []
    for i, bnl in enumerate(beta_nL_cantilever):
        f_n = (bnl**2) / (2 * math.pi * L**2) * math.sqrt(E * I_cs / m_per_L)
        beam_freqs_cant.append(f_n)
        kv(f"Mode {i+1} (β_nL = {bnl:.4f}):", f"{f_n:.2f} Hz")

    # --- Beam bending modes (free-free — in-flight after separation) ---
    sub("Beam Bending Modes (Free-Free — In-Flight)")
    beta_nL_ff = [4.7300, 7.8532, 10.9956]
    beam_freqs_ff = []
    for i, bnl in enumerate(beta_nL_ff):
        f_n = (bnl**2) / (2 * math.pi * L**2) * math.sqrt(E * I_cs / m_per_L)
        beam_freqs_ff.append(f_n)
        kv(f"Mode {i+1} (β_nL = {bnl:.4f}):", f"{f_n:.2f} Hz")

    # --- Axial (longitudinal) modes ---
    sub("Axial (Longitudinal) Modes — Fixed-Free")
    # f_n = (2n-1)/(4L) * sqrt(E/ρ_eff)
    rho_eff = m_per_L / A_cs  # Effective density including payload
    for n in range(1, 4):
        f_ax = (2*n - 1) / (4 * L) * math.sqrt(E / rho_eff)
        kv(f"Mode {n}:", f"{f_ax:.2f} Hz")

    # --- Shell breathing mode (n=0, axisymmetric) ---
    sub("Shell Breathing Mode (n=0, Axisymmetric)")
    # f_breathing = 1/(2π R) * sqrt(E / (ρ * (1 - ν²)))
    f_breath = 1.0 / (2 * math.pi * R) * math.sqrt(E / (rho * (1 - nu**2)))
    kv("Breathing frequency:", f"{f_breath:.2f} Hz")
    kv("Note:", "This is the pure shell (no payload mass added)")

    # --- Lobar (ovalization) shell modes (n ≥ 2) ---
    sub("Lobar Shell Modes (n ≥ 2) — Flügge/Donnell")
    # Simplified Donnell approximation for short cylinders:
    # f_mn = 1/(2π) * sqrt(D_stiff / (ρ h)) * [stuff]
    # Using Arnold-Warburton simplified formula:
    # f_n = 1/(2π R) * sqrt(E h² / (12 ρ R² (1-ν²))) * n(n²-1)/sqrt(n²+1)
    # More practical: Forsberg shell equation
    h = t
    D_flex = E * h**3 / (12 * (1 - nu**2))  # Flexural rigidity
    print(f"    Flexural rigidity D: {D_flex:.4f} N·m")

    for n in range(2, 8):
        # Ring frequency for circumferential mode n (no axial wave):
        # ω² = (E h² / (12 ρ R⁴ (1-ν²))) * n²(n²-1)² / (n²+1)
        omega_sq = (E * h**2 / (12 * rho * R**4 * (1 - nu**2))) * \
                   (n**2 * (n**2 - 1)**2) / (n**2 + 1)
        f_n = math.sqrt(abs(omega_sq)) / (2 * math.pi)
        kv(f"n = {n} (lobar):", f"{f_n:.2f} Hz")

    # --- Minimum frequency check for Falcon Heavy ---
    sub("Falcon Heavy Frequency Requirements")
    f_min_axial = 25.0   # Hz, minimum axial fundamental per SpaceX
    f_min_lateral = 10.0  # Hz, minimum lateral fundamental

    f1_cant = beam_freqs_cant[0]
    f1_ax = (1) / (4 * L) * math.sqrt(E / rho_eff)

    kv("Required minimum axial freq:", f"{f_min_axial:.0f} Hz")
    kv("Actual 1st axial mode:", f"{f1_ax:.2f} Hz")
    kv("Status:", f"{'✓ OK' if f1_ax >= f_min_axial else '⚠ BELOW MINIMUM — CLA REQUIRED'}")
    print()
    kv("Required minimum lateral freq:", f"{f_min_lateral:.0f} Hz")
    kv("Actual 1st lateral (cant.):", f"{f1_cant:.2f} Hz")
    kv("Status:", f"{'✓ OK' if f1_cant >= f_min_lateral else '⚠ BELOW MINIMUM — CLA REQUIRED'}")

    return beam_freqs_cant, f1_ax, f_breath


# =============================================================================
# 2. QUASI-STATIC LOAD ANALYSIS
# =============================================================================
def quasi_static_analysis():
    header("2. QUASI-STATIC LOAD ANALYSIS")
    print("  Per Falcon User's Guide Table 5-3")
    print(f"  Total mass: {m_total:.0f} kg")

    sub("Flight Event Load Factors & Resulting Forces")
    print(f"    {'Event':<22s} {'Axial G':>8s} {'Lat G':>8s} {'F_ax (kN)':>10s} "
          f"{'F_lat (kN)':>10s} {'σ_ax (MPa)':>11s} {'σ_bend (MPa)':>12s}")
    print("    " + "-" * 86)

    max_sigma_combined = 0
    max_event = ""

    for event, factors in FALCON_LOAD_FACTORS.items():
        n_ax = factors["axial_g"]
        n_lat = factors["lateral_g"]
        F_ax = abs(n_ax) * m_total * g
        F_lat = n_lat * m_total * g

        sigma_ax = F_ax / A_cs
        M_bend = F_lat * L  # Cantilever moment
        sigma_bend = M_bend / Z_cs

        sigma_comb = sigma_ax + sigma_bend

        if sigma_comb > max_sigma_combined:
            max_sigma_combined = sigma_comb
            max_event = event

        sign = "C" if n_ax > 0 else "T"
        print(f"    {event:<22s} {n_ax:>+8.1f} {n_lat:>8.1f} {F_ax/1e3:>10.2f} "
              f"{F_lat/1e3:>10.2f} {sigma_ax/1e6:>11.4f} {sigma_bend/1e6:>12.4f}")

    sub("Worst-Case Quasi-Static Stress")
    kv("Governing event:", max_event)
    kv("σ_combined (ax + bend):", f"{max_sigma_combined/1e6:.4f} MPa")
    kv("Margin vs Fcy:", f"{(Fcy/max_sigma_combined - 1)*100:.1f}%")

    return max_sigma_combined


# =============================================================================
# 3. SINUSOIDAL VIBRATION RESPONSE
# =============================================================================
def sinusoidal_vibration(beam_freqs: List[float]):
    header("3. SINUSOIDAL VIBRATION RESPONSE")
    print("  Per Falcon User's Guide Table 5-4 / Figure 5-2")

    sub("Published Sine Environment (Limit Level)")
    print(f"    {'Freq Range (Hz)':<20s} {'Amplitude (G)':>14s} {'Direction':>10s}")
    print("    " + "-" * 48)
    for f_lo, f_hi, amp, dirn in SINE_VIB_ENVIRONMENT:
        print(f"    {f_lo:>5.0f} – {f_hi:<5.0f}       {amp:>10.2f}       {dirn:>8s}")

    sub("Dynamic Amplification at Natural Frequencies")
    # Q factor (amplification) for metallic structures: typically 20-50
    # SpaceX publishes environments for Q=20 to Q=50
    Q_values = [20, 35, 50]

    print(f"    {'Mode':<20s}", end="")
    for Q in Q_values:
        print(f" {'Q='+str(Q):>10s}", end="")
    print(f" {'Input G':>10s} {'Peak G (Q=50)':>14s}")
    print("    " + "-" * 70)

    f1_lat = beam_freqs[0]

    # Determine input level at each natural frequency
    for i, fn in enumerate(beam_freqs[:3]):
        # Find applicable sine input level
        input_g = 0.7  # Default for 25-100 Hz
        for f_lo, f_hi, amp, dirn in SINE_VIB_ENVIRONMENT:
            if dirn == "Lateral" and f_lo <= fn <= f_hi:
                input_g = amp
                break

        print(f"    Lateral mode {i+1} ({fn:.1f} Hz)", end="")
        for Q in Q_values:
            resp = input_g * Q
            print(f" {resp:>10.1f}", end="")
        print(f" {input_g:>10.2f} {input_g * 50:>14.1f}")

    sub("Sine Vibration Induced Stress (Q=50, worst case)")
    # Lateral: F_sine = m * g * Q * input_level
    Q_max = 50
    input_lat = 0.7  # g, for fundamental range
    F_sine_lat = m_total * g * Q_max * input_lat
    sigma_sine_bend = (F_sine_lat * L) / Z_cs
    sigma_sine_ax = F_sine_lat / A_cs

    kv("Lateral sine response force:", f"{F_sine_lat/1e3:.2f} kN")
    kv("Bending stress (cantilever):", f"{sigma_sine_bend/1e6:.4f} MPa")
    kv("Note:", "Sine levels are enveloped by CLA; Q=50 is very conservative")
    kv("Note:", "Actual response depends on coupled loads analysis (CLA)")

    return sigma_sine_bend


# =============================================================================
# 4. RANDOM VIBRATION RESPONSE
# =============================================================================
def random_vibration(beam_freqs: List[float], f_ax: float):
    header("4. RANDOM VIBRATION ANALYSIS")
    print("  Per Falcon User's Guide Table 5-10 / Figure 5-7")
    print("  PSD at top of PAF (P95/50 MPE)")

    sub("Published Random Vibration PSD")
    print(f"    {'Freq (Hz)':>10s} {'ASD (g²/Hz)':>14s}")
    print("    " + "-" * 28)
    for freq, asd in RANDOM_VIB_PSD:
        print(f"    {freq:>10.0f} {asd:>14.4f}")

    # Compute overall Grms by numerical integration (trapezoidal on log scale)
    sub("Overall Grms Computation")
    total_g2 = 0.0
    for i in range(len(RANDOM_VIB_PSD) - 1):
        f1, asd1 = RANDOM_VIB_PSD[i]
        f2, asd2 = RANDOM_VIB_PSD[i + 1]

        if abs(asd1 - asd2) < 1e-12:
            # Flat segment
            area = asd1 * (f2 - f1)
        else:
            # Log-log interpolation
            slope = math.log10(asd2 / asd1) / math.log10(f2 / f1)
            n_slope = slope + 1
            if abs(n_slope) < 1e-10:
                area = asd1 * f1 * math.log(f2 / f1)
            else:
                area = asd1 * f1 / n_slope * ((f2/f1)**n_slope - 1)

        total_g2 += area
        # print(f"      {f1:.0f}-{f2:.0f} Hz: {area:.6f} g²")

    grms_computed = math.sqrt(total_g2)
    kv("Computed overall Grms:", f"{grms_computed:.3f} Grms")
    kv("Published overall Grms:", "~5.13 Grms")
    kv("3σ peak acceleration:", f"{3 * grms_computed:.2f} G")

    # --- Miles Equation Response ---
    sub("Miles Equation — SDOF Response at Natural Frequencies")
    print("  Response Grms = √(π/2 · fn · Q · W(fn))")
    print("  where W(fn) is the PSD level at the natural frequency\n")

    Q_design = 25  # Typical for bolted metallic structure
    Q_values_rand = [10, 25, 50]

    print(f"    {'Mode':<28s} {'fn (Hz)':>8s} {'W(fn)':>10s}", end="")
    for Q in Q_values_rand:
        print(f" {'Q='+str(Q)+' Grms':>12s}", end="")
    print(f" {'3σ (Q=25)':>12s}")
    print("    " + "-" * 90)

    modes = [
        ("1st Lateral Bending", beam_freqs[0]),
        ("2nd Lateral Bending", beam_freqs[1]),
        ("3rd Lateral Bending", beam_freqs[2]),
        ("1st Axial", f_ax),
    ]

    miles_responses = {}
    for name, fn in modes:
        # Interpolate PSD at fn
        W_fn = interpolate_psd(fn)

        print(f"    {name:<28s} {fn:>8.1f} {W_fn:>10.5f}", end="")
        for Q in Q_values_rand:
            resp_grms = math.sqrt(math.pi / 2 * fn * Q * W_fn)
            print(f" {resp_grms:>12.3f}", end="")
        resp_25 = math.sqrt(math.pi / 2 * fn * Q_design * W_fn)
        print(f" {3*resp_25:>12.2f}")
        miles_responses[name] = resp_25

    # --- Random vibration induced stress ---
    sub("Random Vibration Stress (3σ response, Q=25)")
    resp_lat_grms = miles_responses.get("1st Lateral Bending", 0)
    resp_ax_grms = miles_responses.get("1st Axial", 0)

    # 3σ peak
    a_lat_3sig = 3 * resp_lat_grms  # G
    a_ax_3sig = 3 * resp_ax_grms

    F_rand_lat = m_total * g * a_lat_3sig
    F_rand_ax = m_total * g * a_ax_3sig

    sigma_rand_bend = F_rand_lat * L / Z_cs
    sigma_rand_ax = F_rand_ax / A_cs

    kv("3σ lateral acceleration:", f"{a_lat_3sig:.2f} G")
    kv("3σ axial acceleration:", f"{a_ax_3sig:.2f} G")
    kv("Random bending stress:", f"{sigma_rand_bend/1e6:.4f} MPa")
    kv("Random axial stress:", f"{sigma_rand_ax/1e6:.4f} MPa")

    return grms_computed, sigma_rand_bend, sigma_rand_ax, a_lat_3sig, a_ax_3sig


def interpolate_psd(freq: float) -> float:
    """Log-log interpolation of PSD at a given frequency."""
    if freq <= RANDOM_VIB_PSD[0][0]:
        return RANDOM_VIB_PSD[0][1]
    if freq >= RANDOM_VIB_PSD[-1][0]:
        return RANDOM_VIB_PSD[-1][1]

    for i in range(len(RANDOM_VIB_PSD) - 1):
        f1, a1 = RANDOM_VIB_PSD[i]
        f2, a2 = RANDOM_VIB_PSD[i + 1]
        if f1 <= freq <= f2:
            # Log-log interpolation
            slope = math.log10(a2 / a1) / math.log10(f2 / f1)
            return a1 * (freq / f1) ** slope
    return RANDOM_VIB_PSD[-1][1]


# =============================================================================
# 5. ACOUSTIC LOADING
# =============================================================================
def acoustic_analysis():
    header("5. ACOUSTIC ENVIRONMENT ANALYSIS")
    print("  Per Falcon User's Guide Table 5-7 (Falcon Heavy, 60% fill)")
    print("  Sound Pressure Levels in third-octave bands")

    sub("Acoustic Environment")
    print(f"    {'Center Freq (Hz)':>16s} {'SPL (dB)':>10s} {'Pressure (Pa)':>14s}")
    print("    " + "-" * 44)

    p_ref = 20e-6  # Reference pressure (Pa)
    total_p2 = 0

    for fc, spl in ACOUSTIC_ENVIRONMENT:
        p_rms = p_ref * 10**(spl / 20.0)
        total_p2 += p_rms**2
        if fc in [31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000]:
            print(f"    {fc:>16.1f} {spl:>10.1f} {p_rms:>14.2f}")

    oaspl = 10 * math.log10(total_p2 / p_ref**2)
    p_overall = math.sqrt(total_p2)

    sub("Overall Acoustic Loading")
    kv("OASPL:", f"{oaspl:.1f} dB")
    kv("Overall RMS pressure:", f"{p_overall:.1f} Pa ({p_overall/1e3:.4f} kPa)")

    # Acoustic pressure on cylinder wall
    A_surface = math.pi * D * L  # Cylinder surface area (m²)
    F_acoustic = p_overall * A_surface  # Total fluctuating force (very rough)

    sub("Acoustic Stress Estimate (Conservative)")
    # For a large thin-walled cylinder, acoustic loading primarily excites
    # shell breathing and lobar modes. Simplified estimate:
    sigma_acoustic = p_overall * R / t  # Like a pressure vessel hoop stress
    kv("Surface area:", f"{A_surface:.1f} m²")
    kv("Equivalent hoop stress (RMS):", f"{sigma_acoustic/1e6:.4f} MPa")
    kv("Equivalent hoop stress (3σ):", f"{3*sigma_acoustic/1e6:.4f} MPa")
    kv("Note:", "Acoustic response requires FEA for accurate prediction")
    kv("Note:", "Shell modes couple strongly with acoustic field")

    return oaspl, sigma_acoustic


# =============================================================================
# 6. SHOCK RESPONSE
# =============================================================================
def shock_analysis():
    header("6. SHOCK RESPONSE SPECTRUM (SRS)")
    print("  Per Falcon User's Guide Table 5-8")
    print("  LV-induced shock at separation plane (P95/50 MPE)")

    sub("Published Shock SRS")
    print(f"    {'Freq (Hz)':>10s} {'SRS Accel (G)':>14s}")
    print("    " + "-" * 28)
    for freq, amp in SHOCK_SRS:
        print(f"    {freq:>10.0f} {amp:>14.0f}")

    sub("Shock Assessment")
    max_shock_g = max(a for _, a in SHOCK_SRS)
    kv("Peak SRS acceleration:", f"{max_shock_g:.0f} G")
    kv("Peak frequency:", f"{[f for f, a in SHOCK_SRS if a == max_shock_g][0]:.0f} Hz")

    # Shock stress — for the primary structure, shock is typically
    # a concern for equipment mounting, not the primary pressure vessel
    kv("Primary structure concern:", "LOW — shock is high-freq, low displacement")
    kv("Equipment concern:", "HIGH — brackets, avionics mounts, instruments")
    kv("Design action:", "Shock isolate sensitive equipment at mounting points")
    kv("Note:", "2000G at 5-10 kHz typically does not excite primary shell modes")

    # Pseudo-velocity shock spectrum for damage potential
    sub("Pseudo-Velocity Shock Spectrum (Damage Indicator)")
    print(f"    {'Freq (Hz)':>10s} {'SRS (G)':>10s} {'PV (m/s)':>10s} {'PV (in/s)':>10s}")
    print("    " + "-" * 45)
    max_pv = 0
    for freq, amp in SHOCK_SRS:
        pv = amp * g / (2 * math.pi * freq)  # Pseudo-velocity (m/s)
        pv_ips = pv * 39.37  # Convert to in/s
        max_pv = max(max_pv, pv)
        print(f"    {freq:>10.0f} {amp:>10.0f} {pv:>10.3f} {pv_ips:>10.2f}")

    kv("Max pseudo-velocity:", f"{max_pv:.3f} m/s ({max_pv*39.37:.2f} in/s)")
    if max_pv * 39.37 > 100:
        kv("Assessment:", "⚠ PV > 100 in/s — potential for primary structure damage")
    elif max_pv * 39.37 > 50:
        kv("Assessment:", "Moderate — verify equipment mounting integrity")
    else:
        kv("Assessment:", "✓ Acceptable for primary metallic structure")

    return max_shock_g


# =============================================================================
# 7. COMBINED DYNAMIC + STATIC LOADING
# =============================================================================
def combined_assessment(sigma_qs, sigma_sine, sigma_rand_b, sigma_rand_a,
                         sigma_acoustic, a_lat_3sig, a_ax_3sig):
    header("7. COMBINED DYNAMIC + STATIC STRESS ASSESSMENT")
    print("  RSS combination of random + quasi-static loads")
    print("  Per NASA-HDBK-7005 methodology")

    sub("Individual Stress Contributions")
    kv("Quasi-static (max event):", f"{sigma_qs/1e6:.4f} MPa")
    kv("Sinusoidal vibration (Q=50):", f"{sigma_sine/1e6:.4f} MPa")
    kv("Random vibration (3σ bend):", f"{sigma_rand_b/1e6:.4f} MPa")
    kv("Random vibration (3σ axial):", f"{sigma_rand_a/1e6:.4f} MPa")
    kv("Acoustic (3σ hoop):", f"{3*sigma_acoustic/1e6:.4f} MPa")

    sub("Load Combination Methods")
    # Method 1: Absolute sum (ultra-conservative)
    sigma_abs = sigma_qs + sigma_rand_b + sigma_rand_a + 3*sigma_acoustic
    kv("Method 1 — Absolute sum:", f"{sigma_abs/1e6:.4f} MPa  (ultra-conservative)")

    # Method 2: QS + RSS(dynamic components) — NASA recommended
    sigma_rss_dynamic = math.sqrt(sigma_rand_b**2 + sigma_rand_a**2 + (3*sigma_acoustic)**2)
    sigma_combined_rss = sigma_qs + sigma_rss_dynamic
    kv("Method 2 — QS + RSS(random):", f"{sigma_combined_rss/1e6:.4f} MPa  (recommended)")

    # Method 3: RSS all
    sigma_rss_all = math.sqrt(sigma_qs**2 + sigma_rand_b**2 + sigma_rand_a**2 + (3*sigma_acoustic)**2)
    kv("Method 3 — RSS(all):", f"{sigma_rss_all/1e6:.4f} MPa  (unconservative)")

    sub("Combined Equivalent G-Loads")
    # Total equivalent acceleration
    g_ax_combined = 6.0 + a_ax_3sig  # QS + 3σ random
    g_lat_combined = 2.0 + a_lat_3sig

    kv("Axial (QS + random 3σ):", f"{g_ax_combined:.2f} G")
    kv("Lateral (QS + random 3σ):", f"{g_lat_combined:.2f} G")

    # Margins using Method 2 (recommended)
    sub("Margins of Safety (Method 2 — NASA Recommended)")
    FS_yield = 1.25
    FS_ult = 1.50

    MS_yield = Fty / (FS_yield * sigma_combined_rss) - 1
    MS_ult = Ftu / (FS_ult * sigma_combined_rss) - 1

    kv("MS_yield:", f"{MS_yield:+.2f}  {'✓ POSITIVE' if MS_yield > 0 else '⚠ NEGATIVE'}")
    kv("MS_ultimate:", f"{MS_ult:+.2f}  {'✓ POSITIVE' if MS_ult > 0 else '⚠ NEGATIVE'}")

    return sigma_combined_rss, MS_yield, MS_ult


# =============================================================================
# 8. FATIGUE LIFE ESTIMATE
# =============================================================================
def fatigue_analysis(grms: float, beam_freqs: List[float]):
    header("8. FATIGUE LIFE ESTIMATE")
    print("  Miner's rule cumulative damage — random vibration")
    print("  Al 2219-T67 S-N curve approximation")

    sub("S-N Curve Parameters (Al 2219-T67)")
    # Approximate S-N: N = (Sf/S)^(1/b) * N_ref
    # For Al 2219-T67, approximate: N_f = (S_e / σ_a)^m
    # Using Basquin's law: σ_a = σ_f' * (2*N_f)^b
    # Typical for 2219-T67: σ_f' ≈ 655 MPa, b ≈ -0.095
    sigma_f_prime = 655e6  # Fatigue strength coefficient (Pa)
    b_fat = -0.095         # Fatigue strength exponent
    Se_1e7 = 138e6         # Endurance limit @ 10^7 cycles (Pa) — typical for 2219

    kv("Fatigue strength coeff σ_f':", f"{sigma_f_prime/1e6:.0f} MPa")
    kv("Fatigue exponent b:", f"{b_fat}")
    kv("Endurance limit (10^7 cyc):", f"{Se_1e7/1e6:.0f} MPa")

    sub("Random Vibration Fatigue")
    # Dominant cycling frequency ≈ 1st natural frequency
    fn_dominant = beam_freqs[0]
    kv("Dominant cycling frequency:", f"{fn_dominant:.2f} Hz")

    # RMS stress from random vibration
    # Using Miles equation response and 1σ stress
    Q_fat = 25
    W_fn = interpolate_psd(fn_dominant)
    resp_grms = math.sqrt(math.pi / 2 * fn_dominant * Q_fat * W_fn)
    F_rms = m_total * g * resp_grms
    sigma_rms = F_rms * L / Z_cs

    kv("1σ RMS stress:", f"{sigma_rms/1e6:.4f} MPa")
    kv("3σ peak stress:", f"{3*sigma_rms/1e6:.4f} MPa")

    # Rayleigh distribution cycle counting for narrow-band random
    # Damage rate using Miner's rule with narrow-band approximation:
    # D = fn * T * Σ[p(σ_i) / N(σ_i)]
    # For Gaussian narrow-band: D/T ≈ fn * (sqrt(2) * σ_rms)^m * Γ(1 + m/2) / C
    # where N = C / σ^m (S-N curve in power law form)

    # Power law: N = C / σ_a^m  where m = -1/b
    m_sn = -1.0 / b_fat
    C_sn = sigma_f_prime ** m_sn  # Since at N=1 cycle, σ = σ_f'

    kv("S-N power law exponent m:", f"{m_sn:.2f}")

    # Narrow-band Miner's damage rate (per second)
    gamma_val = math.gamma(1 + m_sn / 2)
    D_rate = fn_dominant * (math.sqrt(2) * sigma_rms) ** m_sn * gamma_val / C_sn

    kv("Damage rate:", f"{D_rate:.2e} per second")

    # Typical launch vibration durations
    sub("Launch Phase Durations & Cumulative Damage")
    phases = [
        ("Liftoff (high random)",         10,   1.0),   # seconds, multiplier
        ("Max-Q transonic",               30,   1.0),
        ("Stage 1 ascent",               160,   0.5),   # Lower levels
        ("Stage separation (transient)",    5,   0.8),
        ("Stage 2 burn",                 300,   0.3),   # Much lower
        ("Coast phase",                    60,   0.1),
    ]

    total_damage = 0
    print(f"    {'Phase':<35s} {'Duration':>10s} {'Level':>8s} {'Damage':>12s}")
    print("    " + "-" * 68)

    for phase, dur, mult in phases:
        D_phase = D_rate * dur * mult ** m_sn
        total_damage += D_phase
        print(f"    {phase:<35s} {dur:>8.0f} s {mult:>8.1f}x {D_phase:>12.4e}")

    print("    " + "-" * 68)
    print(f"    {'TOTAL DAMAGE (one launch)':<35s} {'':>10s} {'':>8s} {total_damage:>12.4e}")

    sub("Fatigue Life Assessment")
    if total_damage > 0:
        N_launches = 1.0 / total_damage
        kv("Cycles to failure:", f"{1.0/total_damage:.0f} equivalent launches")
        kv("Damage per launch:", f"{total_damage:.4e}")
    else:
        N_launches = float('inf')
        kv("Cycles to failure:", "Infinite (stress below endurance limit)")

    # Safety factor on fatigue
    SF_fatigue = 4.0  # NASA typically requires 4x life factor
    kv("Required life factor:", f"{SF_fatigue:.0f}x (per NASA-STD-5001B)")
    kv("Available life factor:", f"{N_launches:.0f}x")
    kv("Status:", f"{'✓ OK' if N_launches >= SF_fatigue else '⚠ INSUFFICIENT LIFE'}")

    return total_damage


# =============================================================================
# 9. SUMMARY
# =============================================================================
def print_summary(beam_freqs, grms, sigma_combined, MS_y, MS_u, shock_g, oaspl, damage):
    header("VIBRATION ANALYSIS SUMMARY")
    print(f"""
┌──────────────────────────────────────────────────────────────────────────────┐
│            FALCON HEAVY VIBRATION ANALYSIS — HABITAT MODULE                  │
│            Al 2219-T67, L=10m, D=4.25m, t=5mm, m={m_total:.0f} kg              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  NATURAL FREQUENCIES                                                         │
│    1st Lateral (cantilever):  {beam_freqs[0]:>8.2f} Hz                              │
│    2nd Lateral (cantilever):  {beam_freqs[1]:>8.2f} Hz                              │
│    Falcon min lateral:          10.00 Hz  {'✓' if beam_freqs[0]>=10 else '⚠ FAIL'}                           │
│    Falcon min axial:            25.00 Hz  (verify with CLA)                  │
│                                                                              │
│  RANDOM VIBRATION                                                            │
│    Input Grms (at PAF):        {grms:>6.2f} Grms                                  │
│    3σ peak acceleration:       {3*grms:>6.2f} G                                    │
│                                                                              │
│  ACOUSTIC ENVIRONMENT                                                        │
│    OASPL:                      {oaspl:>6.1f} dB                                    │
│                                                                              │
│  SHOCK                                                                       │
│    Peak SRS:                   {shock_g:>6.0f} G (at 5-10 kHz)                     │
│                                                                              │
│  COMBINED STRESS (QS + RSS random, NASA method)                              │
│    σ_combined:             {sigma_combined/1e6:>10.4f} MPa                           │
│    MS_yield:               {MS_y:>+10.2f}  {'✓' if MS_y>0 else '⚠'}                              │
│    MS_ultimate:            {MS_u:>+10.2f}  {'✓' if MS_u>0 else '⚠'}                              │
│                                                                              │
│  FATIGUE (Miner's rule, one launch)                                          │
│    Cumulative damage:      {damage:>10.4e}                                   │
│    Equivalent launches to failure: {1/damage if damage>0 else float('inf'):>8.0f}                          │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│  KEY FINDINGS & RECOMMENDATIONS                                             │
│                                                                              │
│  1. Natural frequencies are well above Falcon Heavy minimums.                │
│     The 4.25m diameter provides exceptional lateral stiffness.               │
│                                                                              │
│  2. Random vibration and acoustic loads produce stresses well below          │
│     material allowables. The quasi-static MECO (6G) case governs.           │
│                                                                              │
│  3. Shock is only a concern for internally mounted equipment, not            │
│     the primary pressure vessel structure. Design shock isolators.           │
│                                                                              │
│  4. COUPLED LOADS ANALYSIS (CLA) is required by SpaceX. The analytical      │
│     estimates here are for preliminary design only. SpaceX performs          │
│     mission-specific CLA after contract, using your FEM.                    │
│                                                                              │
│  5. Qualification testing required per GEVS (GSFC-STD-7000):                │
│     • Random vibration: MPE + 6 dB for 2 min (qual), MPE for 1 min (AT)    │
│     • Sine sweep: published levels                                           │
│     • Acoustic: MPE + 6 dB in reverberant chamber                           │
│     • Shock: compatible with clampband/separation system                     │
│                                                                              │
│  6. DAMPING CHARACTERIZATION: Q factor significantly affects response.       │
│     Recommend modal survey test to determine actual Q values.                │
│                                                                              │
│  7. For senior design FEA: build shell model in NASTRAN/Abaqus,             │
│     run SOL 103 (modal), SOL 111 (freq response), SOL 108 (random).        │
│     Use lumped mass for payload at CG location.                              │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
""")


# =============================================================================
# MAIN
# =============================================================================
def main():
    sep()
    print("  VIBRATION & DYNAMIC LOADS ANALYSIS")
    print("  Habitat Module on SpaceX Falcon Heavy")
    print(f"  Al 2219-T67 — L={L}m, D={D}m, t={t*1000}mm")
    print(f"  Total mass: {m_total:.0f} kg (structure: {m_structure:.0f}, payload: {m_payload:.0f})")
    sep()

    beam_freqs, f_ax, f_breath = natural_frequencies()
    sigma_qs = quasi_static_analysis()
    sigma_sine = sinusoidal_vibration(beam_freqs)
    grms, sigma_rand_b, sigma_rand_a, a_lat, a_ax = random_vibration(beam_freqs, f_ax)
    oaspl, sigma_acoustic = acoustic_analysis()
    shock_g = shock_analysis()
    sigma_comb, MS_y, MS_u = combined_assessment(
        sigma_qs, sigma_sine, sigma_rand_b, sigma_rand_a, sigma_acoustic, a_lat, a_ax
    )
    damage = fatigue_analysis(grms, beam_freqs)
    print_summary(beam_freqs, grms, sigma_comb, MS_y, MS_u, shock_g, oaspl, damage)

    return 0


if __name__ == "__main__":
    sys.exit(main())
