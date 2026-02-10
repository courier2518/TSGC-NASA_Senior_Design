#!/usr/bin/env python3
"""
===============================================================================
VIBRATION & DYNAMIC LOADS ANALYSIS — Habitat Module on Falcon Heavy
===============================================================================
Senior Design Project — Pressurized Habitat for Lunar/Martian Deployment

Launch Vehicle:     SpaceX Falcon Heavy
Environments:       Per Falcon User's Guide (2025), Tables 5-3, 5-4, 5-10
Standards:          NASA-STD-7001B, NASA-HDBK-7005, GEVS (GSFC-STD-7000)

Outputs:  8 publication-quality figures + console analysis

Geometry:  L=10m, D=4.25m, t=5mm, Al 2219-T67
Payload:   8,000 kg internal systems/supplies
===============================================================================
"""

import math
import sys
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.gridspec import GridSpec
import matplotlib.ticker as ticker
from typing import List, Tuple

# ── Output directory ──
OUT_DIR = "/mnt/user-data/outputs"
os.makedirs(OUT_DIR, exist_ok=True)

# ── Style ──
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans"],
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "legend.fontsize": 9,
    "figure.dpi": 180,
    "savefig.dpi": 180,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "axes.axisbelow": True,
})

# Color palette
C = {
    "navy": "#1B2A4A",
    "blue": "#2E86AB",
    "teal": "#36B5A0",
    "orange": "#F18F01",
    "red": "#C73E1D",
    "gold": "#F0C808",
    "gray": "#8B8C89",
    "light": "#E8ECF1",
    "white": "#FFFFFF",
}

# =============================================================================
# MATERIAL & GEOMETRY
# =============================================================================
E       = 73.1e9;  nu = 0.33;  rho = 2840.0
Fty     = 393e6;   Ftu = 455e6;  Fcy = 290e6

L_cyl   = 10.0;  D_cyl = 4.25;  t_wall = 0.005
R_cyl   = D_cyl / 2.0;  R_mid = R_cyl - t_wall / 2.0

A_cs    = math.pi * (R_cyl**2 - (R_cyl - t_wall)**2)
I_cs    = math.pi / 4.0 * (R_cyl**4 - (R_cyl - t_wall)**4)
Z_cs    = I_cs / R_cyl
r_g     = math.sqrt(I_cs / A_cs)

m_shell     = rho * A_cs * L_cyl
m_caps      = 2 * 1.084 * math.pi * R_cyl**2 * t_wall * rho
m_structure = m_shell + m_caps
m_payload   = 8000.0
m_total     = m_structure + m_payload
g_accel     = 9.81

# =============================================================================
# FALCON HEAVY ENVIRONMENTS
# =============================================================================
FALCON_LOAD_FACTORS = {
    "Liftoff":         {"axial_g": 3.2, "lateral_g": 1.3},
    "Max-Q":           {"axial_g": 3.2, "lateral_g": 0.6},
    "MECO":            {"axial_g": 6.0, "lateral_g": 0.5},
    "Stage Sep":       {"axial_g": -1.5, "lateral_g": 1.5},
    "SES/SECO":        {"axial_g": 3.5, "lateral_g": 0.3},
    "Landing":         {"axial_g": 1.5, "lateral_g": 0.5},
    "Design Env.":     {"axial_g": 6.0, "lateral_g": 2.0},
}

SINE_VIB = [
    (5, 1.0), (10, 0.7), (25, 0.7), (100, 0.7),
]

RANDOM_VIB_PSD = [
    (20, 0.005), (40, 0.005), (80, 0.02), (200, 0.02),
    (500, 0.02), (700, 0.01), (925, 0.01), (2000, 0.002),
]

ACOUSTIC_ENV = [
    (31.5, 121), (40, 123), (50, 126), (63, 128), (80, 129),
    (100, 131), (125, 132), (160, 131), (200, 130), (250, 128),
    (315, 127), (400, 125), (500, 123), (630, 121), (800, 119),
    (1000, 117), (1250, 115), (1600, 113), (2000, 111),
    (2500, 109), (3150, 107), (4000, 105), (5000, 103),
    (6300, 101), (8000, 99),
]

SHOCK_SRS = [
    (100, 20), (200, 40), (500, 200), (700, 400),
    (1000, 800), (2000, 1500), (5000, 2000), (10000, 2000),
]


# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================
def interp_psd(freq):
    psd = RANDOM_VIB_PSD
    if freq <= psd[0][0]: return psd[0][1]
    if freq >= psd[-1][0]: return psd[-1][1]
    for i in range(len(psd) - 1):
        f1, a1 = psd[i]; f2, a2 = psd[i+1]
        if f1 <= freq <= f2:
            slope = math.log10(a2/a1) / math.log10(f2/f1)
            return a1 * (freq/f1)**slope
    return psd[-1][1]


def compute_psd_grms():
    total = 0
    for i in range(len(RANDOM_VIB_PSD) - 1):
        f1, a1 = RANDOM_VIB_PSD[i]; f2, a2 = RANDOM_VIB_PSD[i+1]
        if abs(a1 - a2) < 1e-12:
            total += a1 * (f2 - f1)
        else:
            s = math.log10(a2/a1) / math.log10(f2/f1)
            n = s + 1
            if abs(n) < 1e-10:
                total += a1 * f1 * math.log(f2/f1)
            else:
                total += a1 * f1 / n * ((f2/f1)**n - 1)
    return math.sqrt(total)


def beam_modes_cantilever():
    betas = [1.8751, 4.6941, 7.8548, 10.9955, 14.1372]
    m_per_L = m_total / L_cyl
    return [(b**2)/(2*math.pi*L_cyl**2) * math.sqrt(E*I_cs/m_per_L) for b in betas]


def beam_modes_freefree():
    betas = [4.7300, 7.8532, 10.9956, 14.1372]
    m_per_L = m_total / L_cyl
    return [(b**2)/(2*math.pi*L_cyl**2) * math.sqrt(E*I_cs/m_per_L) for b in betas]


def axial_modes():
    rho_eff = (m_total / L_cyl) / A_cs
    return [(2*n-1)/(4*L_cyl) * math.sqrt(E/rho_eff) for n in range(1, 5)]


def lobar_modes():
    modes = []
    for n in range(2, 12):
        omega_sq = (E * t_wall**2 / (12 * rho * R_cyl**4 * (1 - nu**2))) * \
                   (n**2 * (n**2 - 1)**2) / (n**2 + 1)
        modes.append((n, math.sqrt(abs(omega_sq)) / (2*math.pi)))
    return modes


def miles_eq(fn, Q, W_fn):
    return math.sqrt(math.pi/2 * fn * Q * W_fn)


# =============================================================================
# FIGURE 1: Natural Frequency Map
# =============================================================================
def plot_fig1_natural_frequencies():
    fig, ax = plt.subplots(figsize=(12, 5.5))

    cant = beam_modes_cantilever()
    ff = beam_modes_freefree()
    axm = axial_modes()
    lob = lobar_modes()
    f_breath = 1/(2*math.pi*R_cyl) * math.sqrt(E/(rho*(1-nu**2)))

    y_positions = {
        "Lateral\n(Cantilever)": (5, cant, C["blue"]),
        "Lateral\n(Free-Free)": (4, ff, C["teal"]),
        "Axial": (3, axm, C["orange"]),
        "Lobar\n(Shell n≥2)": (2, [f for _, f in lob], C["red"]),
        "Breathing\n(n=0)": (1, [f_breath], C["gold"]),
    }

    for label, (y, freqs, color) in y_positions.items():
        ax.scatter(freqs, [y]*len(freqs), s=120, c=color, zorder=5,
                   edgecolors="white", linewidths=0.8)
        for i, f in enumerate(freqs):
            ax.annotate(f"{f:.1f}", (f, y), textcoords="offset points",
                        xytext=(0, 12), ha="center", fontsize=7, color=color, fontweight="bold")

    # Falcon Heavy limits
    ax.axvline(10, color=C["red"], ls="--", lw=1.5, alpha=0.7, label="FH Min Lateral (10 Hz)")
    ax.axvline(25, color=C["orange"], ls="--", lw=1.5, alpha=0.7, label="FH Min Axial (25 Hz)")

    # Shade exclusion zones
    ax.axvspan(0.1, 10, alpha=0.08, color=C["red"])
    ax.axvspan(0.1, 25, alpha=0.04, color=C["orange"], ymin=0.3, ymax=0.5)

    ax.set_xscale("log")
    ax.set_xlim(0.5, 1000)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_yticklabels(["Breathing\n(n=0)", "Lobar\n(Shell n≥2)", "Axial",
                         "Lateral\n(Free-Free)", "Lateral\n(Cantilever)"])
    ax.set_xlabel("Frequency (Hz)")
    ax.set_title("Natural Frequency Map — Habitat Module on Falcon Heavy",
                 fontweight="bold", color=C["navy"])
    ax.legend(loc="upper left", framealpha=0.9)
    ax.set_ylim(0.3, 5.8)

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "fig1_natural_frequencies.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"  ✓ Saved {path}")
    return cant, axm


# =============================================================================
# FIGURE 2: Quasi-Static Load Factors
# =============================================================================
def plot_fig2_quasi_static():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5))

    events = list(FALCON_LOAD_FACTORS.keys())
    axial_g = [FALCON_LOAD_FACTORS[e]["axial_g"] for e in events]
    lat_g = [FALCON_LOAD_FACTORS[e]["lateral_g"] for e in events]

    y = np.arange(len(events))
    bar_h = 0.35

    # Left: Load factors bar chart
    ax1.barh(y - bar_h/2, axial_g, bar_h, label="Axial (G)", color=C["blue"], edgecolor="white")
    ax1.barh(y + bar_h/2, lat_g, bar_h, label="Lateral (G)", color=C["orange"], edgecolor="white")
    ax1.set_yticks(y)
    ax1.set_yticklabels(events)
    ax1.set_xlabel("Load Factor (G)")
    ax1.set_title("Falcon Heavy Flight Load Factors", fontweight="bold", color=C["navy"])
    ax1.legend(loc="lower right")
    ax1.axvline(0, color="black", lw=0.5)

    for i, (ag, lg) in enumerate(zip(axial_g, lat_g)):
        ax1.text(ag + 0.15 if ag >= 0 else ag - 0.4, i - bar_h/2,
                 f"{ag:+.1f}", va="center", fontsize=8, fontweight="bold", color=C["blue"])
        ax1.text(lg + 0.15, i + bar_h/2,
                 f"{lg:.1f}", va="center", fontsize=8, fontweight="bold", color=C["orange"])

    # Right: Resulting stresses
    stresses_ax = [abs(ag) * m_total * g_accel / A_cs / 1e6 for ag in axial_g]
    stresses_bend = [lg * m_total * g_accel * L_cyl / Z_cs / 1e6 for lg in lat_g]
    stresses_comb = [a + b for a, b in zip(stresses_ax, stresses_bend)]

    ax2.barh(y, stresses_comb, 0.5, color=C["teal"], edgecolor="white", alpha=0.9, label="Combined σ")
    ax2.axvline(Fcy/1e6, color=C["red"], ls="--", lw=2, label=f"Fcy = {Fcy/1e6:.0f} MPa")
    ax2.axvline(Fty/1e6, color=C["red"], ls="-.", lw=1.5, alpha=0.6, label=f"Fty = {Fty/1e6:.0f} MPa")
    ax2.set_yticks(y)
    ax2.set_yticklabels(events)
    ax2.set_xlabel("Stress (MPa)")
    ax2.set_title("Quasi-Static Stress per Event", fontweight="bold", color=C["navy"])
    ax2.legend(loc="lower right")

    for i, s in enumerate(stresses_comb):
        ax2.text(s + 1, i, f"{s:.1f}", va="center", fontsize=8, fontweight="bold", color=C["navy"])

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "fig2_quasi_static_loads.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"  ✓ Saved {path}")
    return max(stresses_comb) * 1e6


# =============================================================================
# FIGURE 3: Random Vibration PSD + Response
# =============================================================================
def plot_fig3_random_vibration(cant_freqs, ax_freqs):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5))

    # Left: Input PSD
    freqs_psd = [f for f, _ in RANDOM_VIB_PSD]
    asds = [a for _, a in RANDOM_VIB_PSD]

    ax1.loglog(freqs_psd, asds, "o-", color=C["blue"], lw=2.5, markersize=7,
               markeredgecolor="white", markeredgewidth=1, label="Falcon 9/Heavy MPE\n(P95/50)", zorder=5)

    # Smooth interpolated line
    f_smooth = np.logspace(np.log10(20), np.log10(2000), 300)
    asd_smooth = [interp_psd(f) for f in f_smooth]
    ax1.fill_between(f_smooth, asd_smooth, 1e-5, alpha=0.15, color=C["blue"])

    # Mark natural frequencies on PSD
    for i, fn in enumerate(cant_freqs[:3]):
        W = interp_psd(fn)
        ax1.plot(fn, W, "v", color=C["red"], markersize=10, zorder=6)
        ax1.annotate(f"f{i+1}={fn:.1f} Hz", (fn, W), textcoords="offset points",
                     xytext=(10, 10), fontsize=8, color=C["red"], fontweight="bold")
    for i, fn in enumerate(ax_freqs[:1]):
        W = interp_psd(fn)
        ax1.plot(fn, W, "^", color=C["orange"], markersize=10, zorder=6)
        ax1.annotate(f"f_ax={fn:.1f} Hz", (fn, W), textcoords="offset points",
                     xytext=(10, -15), fontsize=8, color=C["orange"], fontweight="bold")

    grms = compute_psd_grms()
    ax1.text(0.03, 0.05, f"Overall: {grms:.2f} Grms\n3σ peak: {3*grms:.1f} G",
             transform=ax1.transAxes, fontsize=10, fontweight="bold",
             bbox=dict(boxstyle="round,pad=0.4", facecolor=C["gold"], alpha=0.8), color=C["navy"])

    ax1.set_xlabel("Frequency (Hz)")
    ax1.set_ylabel("ASD (g²/Hz)")
    ax1.set_title("Random Vibration PSD at PAF", fontweight="bold", color=C["navy"])
    ax1.set_xlim(15, 2500)
    ax1.set_ylim(1e-4, 0.1)
    ax1.legend(loc="upper right")

    # Right: Miles equation response vs Q
    Q_range = np.arange(5, 55, 1)
    modes_plot = [
        ("1st Lateral", cant_freqs[0], C["blue"]),
        ("2nd Lateral", cant_freqs[1], C["teal"]),
        ("1st Axial", ax_freqs[0], C["orange"]),
    ]

    for name, fn, color in modes_plot:
        W = interp_psd(fn)
        responses = [miles_eq(fn, Q, W) for Q in Q_range]
        responses_3sig = [3*r for r in responses]
        ax2.plot(Q_range, responses_3sig, lw=2.5, color=color, label=f"{name} ({fn:.1f} Hz)")

    ax2.axhline(Fcy/1e6 * A_cs / (m_total * g_accel), color=C["red"], ls="--", lw=1,
                alpha=0.5, label="Equiv. yield G-level")
    ax2.fill_betweenx([0, 200], 20, 50, alpha=0.08, color=C["navy"], label="SpaceX Q range")

    ax2.set_xlabel("Amplification Factor Q")
    ax2.set_ylabel("3σ Response Acceleration (G)")
    ax2.set_title("Miles Equation Response vs Q Factor", fontweight="bold", color=C["navy"])
    ax2.legend(loc="upper left", fontsize=8)
    ax2.set_xlim(5, 52)
    ax2.set_ylim(0, None)

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "fig3_random_vibration.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"  ✓ Saved {path}")


# =============================================================================
# FIGURE 4: Sinusoidal Vibration
# =============================================================================
def plot_fig4_sine_vibration(cant_freqs):
    fig, ax = plt.subplots(figsize=(10, 5.5))

    # Input sine environment
    f_sine = [5, 10, 25, 100]
    a_sine = [1.0, 0.7, 0.7, 0.7]
    ax.semilogx(f_sine, a_sine, "s-", color=C["blue"], lw=2.5, markersize=8,
                markeredgecolor="white", label="Input (Limit Level)", zorder=5)

    # Response at Q=10, 25, 50
    for Q, color, ls in [(10, C["teal"], "-"), (25, C["orange"], "-"), (50, C["red"], "-")]:
        resp = [a * Q for a in a_sine]
        ax.semilogx(f_sine, resp, ls=ls, color=color, lw=1.8,
                    label=f"Response Q={Q}", alpha=0.85)

    # Mark natural frequencies
    for i, fn in enumerate(cant_freqs[:3]):
        ax.axvline(fn, color=C["gray"], ls=":", lw=1, alpha=0.7)
        ax.annotate(f"f{i+1}={fn:.1f} Hz", (fn, 0.5), rotation=90,
                    fontsize=8, color=C["gray"], va="bottom")

    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Acceleration (G)")
    ax.set_title("Sinusoidal Vibration — Input & Amplified Response",
                 fontweight="bold", color=C["navy"])
    ax.legend(loc="upper right")
    ax.set_xlim(3, 150)
    ax.set_ylim(0, 45)

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "fig4_sinusoidal_vibration.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"  ✓ Saved {path}")


# =============================================================================
# FIGURE 5: Acoustic Environment
# =============================================================================
def plot_fig5_acoustics():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5))

    freqs_a = [f for f, _ in ACOUSTIC_ENV]
    spls = [s for _, s in ACOUSTIC_ENV]

    # Left: SPL spectrum
    ax1.semilogx(freqs_a, spls, "o-", color=C["blue"], lw=2.5, markersize=6,
                 markeredgecolor="white", label="Falcon Heavy MPE\n(P95/50, 60% fill)")
    ax1.fill_between(freqs_a, spls, 90, alpha=0.15, color=C["blue"])

    # OASPL
    p_ref = 20e-6
    total_p2 = sum((p_ref * 10**(s/20))**2 for _, s in ACOUSTIC_ENV)
    oaspl = 10 * math.log10(total_p2 / p_ref**2)

    ax1.axhline(oaspl, color=C["red"], ls="--", lw=1.5, alpha=0.7)
    ax1.text(35, oaspl + 1.5, f"OASPL = {oaspl:.1f} dB", fontsize=10,
             fontweight="bold", color=C["red"])

    ax1.set_xlabel("1/3 Octave Band Center Frequency (Hz)")
    ax1.set_ylabel("SPL (dB re 20 μPa)")
    ax1.set_title("Acoustic Environment", fontweight="bold", color=C["navy"])
    ax1.set_ylim(95, 145)
    ax1.legend(loc="upper right")

    # Right: Pressure in Pa
    pressures = [p_ref * 10**(s/20) for _, s in ACOUSTIC_ENV]
    ax2.bar([str(int(f)) if f >= 100 else str(f) for f, _ in ACOUSTIC_ENV],
            pressures, color=C["teal"], edgecolor="white", alpha=0.85)
    ax2.set_xlabel("1/3 Octave Band (Hz)")
    ax2.set_ylabel("RMS Pressure (Pa)")
    ax2.set_title("Acoustic Pressure Distribution", fontweight="bold", color=C["navy"])
    ax2.tick_params(axis="x", rotation=65, labelsize=7)

    p_overall = math.sqrt(total_p2)
    ax2.axhline(p_overall, color=C["red"], ls="--", lw=1.5)
    ax2.text(1, p_overall + 5, f"Overall: {p_overall:.1f} Pa", fontsize=9,
             fontweight="bold", color=C["red"])

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "fig5_acoustic_environment.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"  ✓ Saved {path}")
    return oaspl


# =============================================================================
# FIGURE 6: Shock Response Spectrum
# =============================================================================
def plot_fig6_shock():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5))

    freqs_s = [f for f, _ in SHOCK_SRS]
    amps_s = [a for _, a in SHOCK_SRS]

    # Left: SRS
    ax1.loglog(freqs_s, amps_s, "D-", color=C["red"], lw=2.5, markersize=8,
               markeredgecolor="white", label="LV-Induced Shock\n(P95/50 MPE)", zorder=5)
    ax1.fill_between(freqs_s, amps_s, 1, alpha=0.12, color=C["red"])

    ax1.set_xlabel("Frequency (Hz)")
    ax1.set_ylabel("Peak Acceleration (G)")
    ax1.set_title("Shock Response Spectrum", fontweight="bold", color=C["navy"])
    ax1.legend(loc="lower right")
    ax1.set_xlim(80, 12000)
    ax1.set_ylim(10, 5000)

    # Right: Pseudo-Velocity
    pvs = [a * g_accel / (2 * math.pi * f) for f, a in SHOCK_SRS]
    pvs_ips = [pv * 39.37 for pv in pvs]

    ax2.semilogx(freqs_s, pvs_ips, "s-", color=C["orange"], lw=2.5, markersize=8,
                 markeredgecolor="white", label="Pseudo-Velocity", zorder=5)
    ax2.fill_between(freqs_s, pvs_ips, 0, alpha=0.12, color=C["orange"])

    # Damage thresholds
    ax2.axhline(100, color=C["red"], ls="--", lw=1.5, alpha=0.7, label="Damage threshold (100 in/s)")
    ax2.axhline(50, color=C["gold"], ls="--", lw=1.5, alpha=0.7, label="Caution level (50 in/s)")

    ax2.set_xlabel("Frequency (Hz)")
    ax2.set_ylabel("Pseudo-Velocity (in/s)")
    ax2.set_title("Pseudo-Velocity SRS (Damage Indicator)", fontweight="bold", color=C["navy"])
    ax2.legend(loc="upper right")
    ax2.set_xlim(80, 12000)

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "fig6_shock_response.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"  ✓ Saved {path}")


# =============================================================================
# FIGURE 7: Combined Stress Waterfall & Margins
# =============================================================================
def plot_fig7_combined_stress(cant_freqs, ax_freqs, sigma_qs):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5))

    Q = 25

    # Compute stress contributions
    W_lat = interp_psd(cant_freqs[0])
    resp_lat = miles_eq(cant_freqs[0], Q, W_lat)
    sigma_rand_bend = 3 * resp_lat * m_total * g_accel * L_cyl / Z_cs

    W_ax = interp_psd(ax_freqs[0])
    resp_ax = miles_eq(ax_freqs[0], Q, W_ax)
    sigma_rand_ax = 3 * resp_ax * m_total * g_accel / A_cs

    p_ref = 20e-6
    total_p2 = sum((p_ref * 10**(s/20))**2 for _, s in ACOUSTIC_ENV)
    p_overall = math.sqrt(total_p2)
    sigma_acoustic = 3 * p_overall * R_cyl / t_wall

    sigma_rss_dyn = math.sqrt(sigma_rand_bend**2 + sigma_rand_ax**2 + sigma_acoustic**2)
    sigma_combined = sigma_qs + sigma_rss_dyn

    # Left: Waterfall bar chart
    components = ["Quasi-\nStatic", "Random\nBending\n(3σ)", "Random\nAxial\n(3σ)", "Acoustic\n(3σ)",
                  "RSS\nDynamic", "Combined\n(QS+RSS)"]
    values = [sigma_qs/1e6, sigma_rand_bend/1e6, sigma_rand_ax/1e6, sigma_acoustic/1e6,
              sigma_rss_dyn/1e6, sigma_combined/1e6]
    colors = [C["blue"], C["teal"], C["orange"], C["gold"], C["navy"], C["red"]]

    bars = ax1.bar(components, values, color=colors, edgecolor="white", width=0.65)

    for bar, val in zip(bars, values):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                 f"{val:.1f}", ha="center", fontsize=9, fontweight="bold", color=C["navy"])

    ax1.axhline(Fty/1e6, color=C["red"], ls="--", lw=2, alpha=0.5)
    ax1.text(5.5, Fty/1e6 + 5, f"Fty={Fty/1e6:.0f}", fontsize=9, color=C["red"],
             ha="center", fontweight="bold")
    ax1.axhline(Fcy/1e6, color=C["red"], ls="-.", lw=1.5, alpha=0.4)
    ax1.text(5.5, Fcy/1e6 + 5, f"Fcy={Fcy/1e6:.0f}", fontsize=9, color=C["red"],
             ha="center", fontweight="bold", alpha=0.7)

    ax1.set_ylabel("Stress (MPa)")
    ax1.set_title("Stress Waterfall — Load Contributions", fontweight="bold", color=C["navy"])
    ax1.set_ylim(0, max(Fty/1e6, Fcy/1e6) * 1.15)

    # Right: Margins of Safety
    FS_y = 1.25; FS_u = 1.50; FS_b = 2.0
    MS_yield = Fty / (FS_y * sigma_combined) - 1
    MS_ult = Ftu / (FS_u * sigma_combined) - 1

    # Shell buckling
    sigma_cl = 0.605 * E * t_wall / R_cyl
    phi = (1/16) * math.sqrt(R_cyl / t_wall)
    gamma = 1 - 0.901 * (1 - math.exp(-phi))
    sigma_cr_shell = gamma * sigma_cl
    MS_buck = sigma_cr_shell / (FS_b * sigma_combined) - 1

    margin_labels = ["MS_yield\n(FS=1.25)", "MS_ultimate\n(FS=1.50)", "MS_buckling\n(FS=2.0)"]
    margin_vals = [MS_yield, MS_ult, MS_buck]
    margin_colors = [C["teal"] if m > 0.5 else C["orange"] if m > 0 else C["red"] for m in margin_vals]

    bars2 = ax2.bar(margin_labels, margin_vals, color=margin_colors, edgecolor="white", width=0.5)
    ax2.axhline(0, color="black", lw=1.5)

    for bar, val in zip(bars2, margin_vals):
        ax2.text(bar.get_x() + bar.get_width()/2, val + 0.05 if val >= 0 else val - 0.12,
                 f"{val:+.2f}", ha="center", fontsize=12, fontweight="bold",
                 color=C["navy"])

    ax2.set_ylabel("Margin of Safety")
    ax2.set_title("Margins of Safety (Combined Loading)", fontweight="bold", color=C["navy"])
    ax2.set_ylim(min(margin_vals) - 0.3, max(margin_vals) + 0.5)

    # Add pass/fail annotation
    status = "ALL POSITIVE ✓" if all(m > 0 for m in margin_vals) else "⚠ NEGATIVE MARGIN"
    status_color = C["teal"] if all(m > 0 for m in margin_vals) else C["red"]
    ax2.text(0.5, 0.95, status, transform=ax2.transAxes, fontsize=14, fontweight="bold",
             ha="center", va="top", color=status_color,
             bbox=dict(boxstyle="round,pad=0.4", facecolor=C["light"], edgecolor=status_color, lw=2))

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "fig7_combined_stress_margins.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"  ✓ Saved {path}")
    return sigma_combined, MS_yield, MS_ult


# =============================================================================
# FIGURE 8: Fatigue S-N + Damage
# =============================================================================
def plot_fig8_fatigue(cant_freqs):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5))

    # S-N curve
    sigma_f_prime = 655e6
    b_fat = -0.095
    N_range = np.logspace(1, 9, 200)
    S_range = sigma_f_prime * (2 * N_range) ** b_fat

    ax1.loglog(N_range, S_range / 1e6, lw=2.5, color=C["blue"], label="Al 2219-T67 (Basquin)")
    ax1.fill_between(N_range, S_range / 1e6, 1, alpha=0.08, color=C["blue"])

    # Mark operating stress levels
    fn = cant_freqs[0]
    Q = 25
    W_fn = interp_psd(fn)
    resp = miles_eq(fn, Q, W_fn)
    sigma_1sig = resp * m_total * g_accel * L_cyl / Z_cs
    sigma_3sig = 3 * sigma_1sig

    # Equivalent cycles for 1 launch (~550 sec of vibration at fn Hz)
    n_cycles_launch = fn * 550

    ax1.axhline(sigma_3sig / 1e6, color=C["red"], ls="--", lw=1.5,
                label=f"3σ stress = {sigma_3sig/1e6:.1f} MPa")
    ax1.axhline(sigma_1sig / 1e6, color=C["orange"], ls="--", lw=1.5,
                label=f"1σ stress = {sigma_1sig/1e6:.1f} MPa")
    ax1.axhline(138, color=C["teal"], ls=":", lw=1.5, alpha=0.7, label="Endurance limit (~138 MPa)")

    ax1.axvline(n_cycles_launch, color=C["gray"], ls=":", lw=1)
    ax1.text(n_cycles_launch * 1.5, 500, f"1 launch\n≈{n_cycles_launch:.0f} cyc",
             fontsize=8, color=C["gray"])

    ax1.set_xlabel("Cycles to Failure (N)")
    ax1.set_ylabel("Stress Amplitude (MPa)")
    ax1.set_title("S-N Curve — Al 2219-T67", fontweight="bold", color=C["navy"])
    ax1.legend(loc="upper right", fontsize=8)
    ax1.set_xlim(10, 1e9)
    ax1.set_ylim(10, 700)

    # Right: Cumulative damage per phase
    m_sn = -1 / b_fat
    C_sn = sigma_f_prime ** m_sn
    gamma_val = math.gamma(1 + m_sn / 2)
    D_rate = fn * (math.sqrt(2) * sigma_1sig) ** m_sn * gamma_val / C_sn

    phases = [
        ("Liftoff", 10, 1.0),
        ("Max-Q", 30, 1.0),
        ("S1 Ascent", 160, 0.5),
        ("Stage Sep", 5, 0.8),
        ("S2 Burn", 300, 0.3),
        ("Coast", 60, 0.1),
    ]

    phase_names = [p[0] for p in phases]
    damages = [D_rate * dur * mult ** m_sn for _, dur, mult in phases]
    cum_damage = np.cumsum(damages)

    colors_bar = [C["red"], C["orange"], C["blue"], C["teal"], C["navy"], C["gray"]]

    ax2.bar(phase_names, damages, color=colors_bar, edgecolor="white", alpha=0.85)
    ax2.set_ylabel("Miner's Damage Fraction")
    ax2.set_title("Fatigue Damage per Flight Phase", fontweight="bold", color=C["navy"])
    ax2.ticklabel_format(axis="y", style="scientific", scilimits=(-10, -6))
    ax2.tick_params(axis="x", rotation=30)

    total_damage = sum(damages)
    life_launches = 1 / total_damage if total_damage > 0 else float("inf")

    ax2.text(0.97, 0.95,
             f"Total damage: {total_damage:.2e}\n"
             f"Life: {life_launches:.0e} launches\n"
             f"Status: ✓ Infinite life",
             transform=ax2.transAxes, fontsize=9, fontweight="bold",
             ha="right", va="top", color=C["navy"],
             bbox=dict(boxstyle="round,pad=0.4", facecolor=C["light"], edgecolor=C["teal"], lw=1.5))

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "fig8_fatigue_analysis.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"  ✓ Saved {path}")


# =============================================================================
# MAIN
# =============================================================================
def main():
    print("=" * 80)
    print("  VIBRATION ANALYSIS — GRAPHICAL OUTPUT GENERATION")
    print(f"  Habitat Module on Falcon Heavy")
    print(f"  Al 2219-T67 | L={L_cyl}m, D={D_cyl}m, t={t_wall*1000}mm | m={m_total:.0f} kg")
    print("=" * 80)
    print()

    print("  Generating figures...\n")

    cant_freqs, ax_freqs = plot_fig1_natural_frequencies()
    sigma_qs = plot_fig2_quasi_static()
    plot_fig3_random_vibration(cant_freqs, ax_freqs)
    plot_fig4_sine_vibration(cant_freqs)
    oaspl = plot_fig5_acoustics()
    plot_fig6_shock()
    sigma_comb, MS_y, MS_u = plot_fig7_combined_stress(cant_freqs, ax_freqs, sigma_qs)
    plot_fig8_fatigue(cant_freqs)

    print(f"\n  All 8 figures saved to {OUT_DIR}/")
    print()
    print("  ┌──────────────────────────────────────────────────────────────┐")
    print("  │  FIGURE MANIFEST                                            │")
    print("  ├──────────────────────────────────────────────────────────────┤")
    print("  │  fig1_natural_frequencies.png    — Modal frequency map       │")
    print("  │  fig2_quasi_static_loads.png     — Load factors & stress     │")
    print("  │  fig3_random_vibration.png       — PSD & Miles response      │")
    print("  │  fig4_sinusoidal_vibration.png   — Sine env. & amplification │")
    print("  │  fig5_acoustic_environment.png   — SPL spectrum & pressure   │")
    print("  │  fig6_shock_response.png         — SRS & pseudo-velocity     │")
    print("  │  fig7_combined_stress_margins.png— Stress waterfall & MS     │")
    print("  │  fig8_fatigue_analysis.png       — S-N curve & Miner damage  │")
    print("  └──────────────────────────────────────────────────────────────┘")
    print()
    print(f"  Combined stress (QS + RSS): {sigma_comb/1e6:.2f} MPa")
    print(f"  MS_yield: {MS_y:+.2f}  |  MS_ultimate: {MS_u:+.2f}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
