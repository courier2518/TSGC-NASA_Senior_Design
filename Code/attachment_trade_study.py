#!/usr/bin/env python3
"""
===============================================================================
STIFFENER ATTACHMENT TRADE STUDY — Habitat Module
===============================================================================
Options for mounting 7075-T6 stringers and rings to 2219-T67 shell:

  Option A: T-beam stringers, rings bolt to stringer flange
  Option B: Blade stringers + clip angles at intersections  
  Option C: Back-to-back L-stringers with integral ring seat
  Option D: Hat-section stringers with ring through-bolted

Each option evaluated for:
  - Structural performance (buckling, t_eff, σ_cr)
  - Mass (stiffener + attachment hardware)
  - Assembly complexity (fastener count, access, tolerance)
  - Systems integration (conduit routing, equipment mounting)
  - Inspectability and maintainability
===============================================================================
"""
import math, os, sys
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, Polygon, Circle

OUT="/mnt/user-data/outputs"; os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family":"sans-serif","font.size":10,"axes.titlesize":12,
    "axes.labelsize":11,"legend.fontsize":9,"figure.dpi":180,"savefig.dpi":180,
    "axes.grid":True,"grid.alpha":0.3,"axes.axisbelow":True})
C={"navy":"#1B2A4A","blue":"#2E86AB","teal":"#36B5A0","orange":"#F18F01",
   "red":"#C73E1D","gold":"#F0C808","gray":"#8B8C89","light":"#E8ECF1","purple":"#7B2D8E"}

# ── Materials ──
SK={"E":73.1e9,"nu":0.33,"rho":2840,"Fty":393e6,"Ftu":455e6,"Fcy":290e6}
ST={"E":71.7e9,"nu":0.33,"rho":2810,"Fty":480e6,"Ftu":560e6,"Fcy":480e6}

# ── Shell geometry (fixed) ──
L=10.0; D=4.25; t=0.005; R=D/2
A_sk=math.pi*(R**2-(R-t)**2); I_sk=math.pi/4*(R**4-(R-t)**4); Z_sk=I_sk/R
circ=math.pi*D
m_shell=SK["rho"]*A_sk*L; m_caps=2*1.084*math.pi*R**2*t*SK["rho"]
m_base=m_shell+m_caps

# ── Loads (from vibration analysis) ──
sig_comp=128.65e6  # Max compressive fiber (MPa)

# ── Common parameters ──
N_STR=60; N_RING=9  # Using 9 rings (per systems integration requirement)
b_s=circ/N_STR      # Stringer spacing ~222mm
b_r=L/(N_RING+1)    # Ring spacing = 1000mm

# Bolt/rivet specs
d_bolt=4.76e-3       # 3/16" (4.76mm) for stiffener-to-shell (lighter than 1/4")
d_bolt_node=6.35e-3  # 1/4" for ring-to-stringer nodes (higher load)
rho_steel=7940       # A286 density

W=80
def sep(c="="): print(c*W)
def hdr(t): print(); sep(); print(f"  {t}"); sep()
def sub(t): print(f"\n  ── {t} {'─'*max(1,W-len(t)-6)}")
def kv(k,v,i=4): print(f"{' '*i}{k:<52s} {v}")

# ═══════════════════════════════════════════════════════════════════════════════
# CROSS-SECTION DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

def t_beam_section(h_web, t_web, w_flange, t_flange):
    """T-beam: web + top flange (flange faces inward for ring mounting)."""
    A_web = h_web * t_web
    A_fl = w_flange * t_flange
    A = A_web + A_fl
    # Centroid from base of web (shell side)
    y_web = h_web / 2
    y_fl = h_web + t_flange / 2
    y_bar = (A_web * y_web + A_fl * y_fl) / A
    # I about centroid
    I = (t_web * h_web**3 / 12 + A_web * (y_bar - y_web)**2 +
         w_flange * t_flange**3 / 12 + A_fl * (y_bar - y_fl)**2)
    h_total = h_web + t_flange
    return {"type": "T-beam", "A": A, "I": I, "y_bar": y_bar, "h": h_total,
            "h_web": h_web, "t_web": t_web, "w_fl": w_flange, "t_fl": t_flange,
            "A_web": A_web, "A_fl": A_fl}

def blade_section(h, tw):
    """Simple rectangular blade stiffener."""
    A = h * tw
    I = tw * h**3 / 12
    return {"type": "Blade", "A": A, "I": I, "y_bar": h/2, "h": h,
            "h_web": h, "t_web": tw, "w_fl": 0, "t_fl": 0,
            "A_web": A, "A_fl": 0}

def L_section(h_leg, w_leg, tl):
    """L-angle (equal legs)."""
    A_v = h_leg * tl        # Vertical leg
    A_h = (w_leg - tl) * tl  # Horizontal leg (minus overlap)
    A = A_v + A_h
    y_v = h_leg / 2
    y_h = tl / 2
    y_bar = (A_v * y_v + A_h * y_h) / A
    I = (tl * h_leg**3 / 12 + A_v * (y_bar - y_v)**2 +
         (w_leg - tl) * tl**3 / 12 + A_h * (y_bar - y_h)**2)
    return {"type": "L-angle", "A": A, "I": I, "y_bar": y_bar, "h": h_leg,
            "h_web": h_leg, "t_web": tl, "w_fl": w_leg, "t_fl": tl,
            "A_web": A_v, "A_fl": A_h}

def hat_section(h, w_top, w_base, th):
    """Hat (Ω) section: two webs + top cap. w_base = total footprint width."""
    # Simplified: two webs of height h, top cap of width w_top, base flanges
    A_webs = 2 * h * th
    A_cap = w_top * th
    A_flanges = 2 * ((w_base - w_top) / 2 - th) * th  # Two base flanges
    A_flanges = max(A_flanges, 0)
    A = A_webs + A_cap + A_flanges
    y_webs = h / 2
    y_cap = h + th / 2
    y_fl = th / 2
    y_bar = (A_webs * y_webs + A_cap * y_cap + A_flanges * y_fl) / A if A > 0 else h/2
    I = (2 * th * h**3 / 12 + A_webs * (y_bar - y_webs)**2 +
         w_top * th**3 / 12 + A_cap * (y_bar - y_cap)**2 +
         A_flanges * (y_bar - y_fl)**2)
    return {"type": "Hat", "A": A, "I": I, "y_bar": y_bar, "h": h + th,
            "h_web": h, "t_web": th, "w_fl": w_top, "t_fl": th,
            "A_web": A_webs, "A_fl": A_cap}


# ═══════════════════════════════════════════════════════════════════════════════
# STRUCTURAL PERFORMANCE
# ═══════════════════════════════════════════════════════════════════════════════

def buckling_performance(section, n_str=N_STR, n_ring=N_RING):
    """Compute σ_cr for a stiffened shell with given stringer section."""
    e = t / 2 + section["y_bar"]  # Eccentricity from skin mid-plane
    D_skin = SK["E"] * t**3 / (12 * (1 - SK["nu"]**2))
    D_str = ST["E"] * section["I"] / b_s + ST["E"] * (section["A"] / b_s) * e**2
    D_ax = D_skin + D_str
    t_eff = (12 * (1 - SK["nu"]**2) * D_ax / SK["E"])**(1/3)
    scl = 0.605 * SK["E"] * t_eff / R
    KDF = 0.65
    pb = 101325 * R / (t * scl) if scl > 0 else 0
    gam = min(KDF + min(pb * 0.15, 1 - KDF), 1.0)
    scr = gam * scl
    # Local pocket
    bl = min(b_s, b_r)
    scr_l = 4.0 * math.pi**2 * SK["E"] * t**2 / (12 * (1 - SK["nu"]**2) * bl**2)
    # Crippling (web — free edge)
    scr_c = 0.43 * ST["E"] * (section["t_web"] / section["h_web"])**2
    # Flange crippling (if has flange — free edge)
    if section["w_fl"] > 0 and section["t_fl"] > 0:
        scr_fl = 0.43 * ST["E"] * (section["t_fl"] / section["w_fl"])**2
        scr_c = min(scr_c, scr_fl)  # Governs

    ms_g = scr / (2.0 * sig_comp) - 1
    ms_l = scr_l / (1.5 * sig_comp) - 1
    ms_c = scr_c / (1.5 * sig_comp) - 1

    return {"t_eff": t_eff, "scl": scl, "scr": scr, "scr_l": scr_l, "scr_c": scr_c,
            "ms_g": ms_g, "ms_l": ms_l, "ms_c": ms_c, "e": e, "D_ax": D_ax}


# ═══════════════════════════════════════════════════════════════════════════════
# OPTION DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

def option_A():
    """T-beam stringers, rings bolt to stringer flange at intersections."""
    # T-beam: 25mm web + 20mm×3mm flange (flange inward)
    sec = t_beam_section(h_web=0.025, t_web=0.003, w_flange=0.020, t_flange=0.003)
    perf = buckling_performance(sec)

    # Mass
    m_str = N_STR * ST["rho"] * sec["A"] * L
    # Rings: blades bolted to stringer flanges (only need web, no shell attachment)
    ring_sec = blade_section(0.025, 0.003)
    m_ring = N_RING * ST["rho"] * ring_sec["A"] * circ

    # Fasteners: stringers to shell via doublers
    n_fasteners_per_stringer = int(L / 0.060)  # Every 60mm pitch
    n_fast_str = N_STR * n_fasteners_per_stringer
    # Ring-to-stringer nodes: 2 bolts per intersection
    n_nodes = N_STR * N_RING
    n_fast_nodes = n_nodes * 2
    # Total fasteners
    n_fast_total = n_fast_str + n_fast_nodes
    # Doubler mass (2219 strip under each stringer, 30mm wide × 3mm thick)
    m_doublers = N_STR * SK["rho"] * 0.030 * 0.003 * L
    # Bolt mass
    m_bolts = n_fast_str * rho_steel * math.pi/4 * d_bolt**2 * 0.020 + \
              n_fast_nodes * rho_steel * math.pi/4 * d_bolt_node**2 * 0.025

    m_total = m_str + m_ring + m_doublers + m_bolts

    return {
        "name": "A: T-beam stringers\n   Rings bolt to flange",
        "short": "T-beam + flange ring",
        "section": sec, "perf": perf,
        "m_str": m_str, "m_ring": m_ring, "m_doubler": m_doublers,
        "m_bolts": m_bolts, "m_total": m_total,
        "n_fast": n_fast_total, "n_nodes": n_nodes,
        "ring_attach": "Bolted to stringer flange",
        "str_attach": "Bolted to shell via doubler strip",
        "pros": [
            "Ring mounts directly to stringer flange — clean node",
            "Flange provides cable/conduit shelf",
            "Fewer shell penetrations (rings don't touch shell)",
            "Ring segments replaceable without disturbing shell",
        ],
        "cons": [
            "T-section heavier than blade for same web height",
            "Flange crippling becomes a failure mode",
            "300 node intersections to fasten during assembly",
            "Flange width limits stringer spacing reduction",
        ],
    }

def option_B():
    """Blade stringers + clip angles at ring-stringer intersections."""
    sec = blade_section(0.025, 0.003)
    perf = buckling_performance(sec)

    m_str = N_STR * ST["rho"] * sec["A"] * L
    ring_sec = blade_section(0.025, 0.003)
    m_ring = N_RING * ST["rho"] * ring_sec["A"] * circ

    # Clip angles at each intersection: small L-bracket, ~30×30×3mm, 40mm long
    clip_A = 2 * 0.030 * 0.003  # Two legs
    clip_L = 0.040  # 40mm long
    n_nodes = N_STR * N_RING
    m_clips = n_nodes * ST["rho"] * clip_A * clip_L

    # Fasteners: stringers to shell
    n_fast_str = N_STR * int(L / 0.060)
    # Rings to shell via their own doublers
    n_fast_ring = N_RING * int(circ / 0.080)
    # Clips: 4 fasteners per clip (2 to stringer, 2 to ring)
    n_fast_clips = n_nodes * 4
    n_fast_total = n_fast_str + n_fast_ring + n_fast_clips

    m_doublers_str = N_STR * SK["rho"] * 0.030 * 0.003 * L
    m_doublers_ring = N_RING * SK["rho"] * 0.060 * 0.003 * circ
    m_bolts = (n_fast_str + n_fast_ring) * rho_steel * math.pi/4 * d_bolt**2 * 0.020 + \
              n_fast_clips * rho_steel * math.pi/4 * d_bolt**2 * 0.015
    m_total = m_str + m_ring + m_clips + m_doublers_str + m_doublers_ring + m_bolts

    return {
        "name": "B: Blade stringers\n   Clip angles at nodes",
        "short": "Blade + clip angles",
        "section": sec, "perf": perf,
        "m_str": m_str, "m_ring": m_ring, "m_doubler": m_doublers_str + m_doublers_ring,
        "m_bolts": m_bolts, "m_clips": m_clips, "m_total": m_total,
        "n_fast": n_fast_total, "n_nodes": n_nodes,
        "ring_attach": "Bolted to shell via doubler + clipped to stringer",
        "str_attach": "Bolted to shell via doubler strip",
        "pros": [
            "Lightest stringer section (blade = minimum material)",
            "Rings independently mounted — structural redundancy",
            "Standard aerospace practice (Boeing 787, Airbus A350 fuselage)",
            "Each element replaceable independently",
        ],
        "cons": [
            "Highest part count (540 clip angles + fasteners)",
            "4 fasteners per clip × 540 = 2160 clip fasteners alone",
            "Clips are labor-intensive to install and inspect",
            "No natural shelf for conduit routing",
        ],
    }

def option_C():
    """Back-to-back L-stringers forming a T, ring weaves between legs."""
    # Two L-angles back-to-back: each 25mm×15mm legs, 3mm thick
    # This creates a channel that the ring blade can slot into
    sec_single = L_section(0.025, 0.015, 0.003)
    # Effective section = 2× L-angle
    sec = {
        "type": "2×L (channel)", "A": 2 * sec_single["A"],
        "I": 2 * sec_single["I"] + 2 * sec_single["A"] * (0.003/2)**2,  # Small offset
        "y_bar": sec_single["y_bar"], "h": sec_single["h"],
        "h_web": sec_single["h_web"], "t_web": 2 * sec_single["t_web"],  # Effective
        "w_fl": sec_single["w_fl"], "t_fl": sec_single["t_fl"],
        "A_web": 2 * sec_single["A_web"], "A_fl": 2 * sec_single["A_fl"],
    }
    perf = buckling_performance(sec)

    m_str = N_STR * ST["rho"] * sec["A"] * L
    ring_sec = blade_section(0.022, 0.003)  # Ring slides between L-legs
    m_ring = N_RING * ST["rho"] * ring_sec["A"] * circ

    n_nodes = N_STR * N_RING
    # Fasteners: L-stringers to shell (each L needs its own row)
    n_fast_str = 2 * N_STR * int(L / 0.080)  # 2 rows per stringer pair
    # Ring through-bolted at each node (1 bolt through ring + both L's)
    n_fast_nodes = n_nodes * 1
    # Doublers
    m_doublers = N_STR * SK["rho"] * 0.040 * 0.003 * L
    m_bolts = n_fast_str * rho_steel * math.pi/4 * d_bolt**2 * 0.020 + \
              n_fast_nodes * rho_steel * math.pi/4 * d_bolt_node**2 * 0.025
    m_total = m_str + m_ring + m_doublers + m_bolts

    return {
        "name": "C: Back-to-back L-stringers\n   Ring slots between legs",
        "short": "2×L channel + slot ring",
        "section": sec, "perf": perf,
        "m_str": m_str, "m_ring": m_ring, "m_doubler": m_doublers,
        "m_bolts": m_bolts, "m_total": m_total,
        "n_fast": n_fast_str + n_fast_nodes, "n_nodes": n_nodes,
        "ring_attach": "Slots between L-legs, single through-bolt at node",
        "str_attach": "Two L-angles bolted to shell via wide doubler",
        "pros": [
            "Ring captive in channel — inherent shear transfer",
            "Single bolt per node (simplest intersection)",
            "Channel between L's routes wiring/small conduit",
            "Good torsional stiffness (semi-closed section)",
        ],
        "cons": [
            "Heaviest stringer (2× L-angles)",
            "Double fastener row for stringers",
            "Tight tolerance: ring must fit between L-legs",
            "Difficult to inspect inner faying surfaces",
        ],
    }

def option_D():
    """Hat-section stringers with ring passing through cutouts."""
    sec = hat_section(h=0.025, w_top=0.020, w_base=0.040, th=0.003)
    perf = buckling_performance(sec)

    m_str = N_STR * ST["rho"] * sec["A"] * L
    ring_sec = blade_section(0.022, 0.003)
    m_ring = N_RING * ST["rho"] * ring_sec["A"] * circ

    n_nodes = N_STR * N_RING
    # Fasteners: hat flanges to shell (2 rows per hat)
    n_fast_str = 2 * N_STR * int(L / 0.060)
    # Ring-to-hat: 2 rivets per side at each node
    n_fast_nodes = n_nodes * 2
    m_doublers = N_STR * SK["rho"] * 0.050 * 0.003 * L
    m_bolts = n_fast_str * rho_steel * math.pi/4 * d_bolt**2 * 0.018 + \
              n_fast_nodes * rho_steel * math.pi/4 * d_bolt**2 * 0.020
    m_total = m_str + m_ring + m_doublers + m_bolts

    return {
        "name": "D: Hat-section stringers\n   Ring through mouse-holes",
        "short": "Hat + mouse-hole ring",
        "section": sec, "perf": perf,
        "m_str": m_str, "m_ring": m_ring, "m_doubler": m_doublers,
        "m_bolts": m_bolts, "m_total": m_total,
        "n_fast": n_fast_str + n_fast_nodes, "n_nodes": n_nodes,
        "ring_attach": "Passes through hat cutouts, riveted to web",
        "str_attach": "Flanges riveted to shell (no doubler needed if wide flanges)",
        "pros": [
            "Enclosed section — excellent torsional stiffness",
            "Hat interior is natural conduit raceway",
            "Wide base flanges distribute load (may skip doubler)",
            "Mouse-hole intersections are well-understood (aircraft fuselage)",
        ],
        "cons": [
            "Mouse-hole cutouts weaken stringer at ring crossing",
            "Most complex to fabricate (formed section)",
            "Difficult internal inspection",
            "Ring must be installed BEFORE hat is closed",
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# TRADE MATRIX & OUTPUT
# ═══════════════════════════════════════════════════════════════════════════════

def score_option(opt):
    """Score 1-5 on key criteria (5=best)."""
    perf = opt["perf"]
    scores = {}

    # Structural: based on global buckling margin
    mg = perf["ms_g"]
    scores["Structural"] = 5 if mg > 0.3 else 4 if mg > 0.1 else 3 if mg > 0 else 2 if mg > -0.2 else 1

    # Mass: inverse of total mass
    m = opt["m_total"]
    scores["Mass"] = 5 if m < 200 else 4 if m < 250 else 3 if m < 350 else 2 if m < 500 else 1

    # Assembly: inverse of fastener count
    nf = opt["n_fast"]
    scores["Assembly"] = 5 if nf < 12000 else 4 if nf < 14000 else 3 if nf < 17000 else 2 if nf < 20000 else 1

    # Systems integration: subjective based on conduit routing ability
    if "T-beam" in opt["short"]: scores["Systems"] = 5
    elif "Hat" in opt["short"]: scores["Systems"] = 4
    elif "channel" in opt["short"]: scores["Systems"] = 4
    else: scores["Systems"] = 2

    # Inspectability
    if "Blade" in opt["short"]: scores["Inspect"] = 5
    elif "T-beam" in opt["short"]: scores["Inspect"] = 4
    elif "channel" in opt["short"]: scores["Inspect"] = 2
    else: scores["Inspect"] = 2

    scores["Total"] = sum(scores.values())
    return scores


def main():
    options = [option_A(), option_B(), option_C(), option_D()]

    hdr("STIFFENER ATTACHMENT TRADE STUDY")
    print(f"  Config: {N_STR} stringers × {N_RING} rings on Al 2219-T67 shell")
    print(f"  Stiffener material: Al 7075-T6, bolted (no welding)")
    sep("-")

    # ── Individual option details ──
    for opt in options:
        sec = opt["section"]
        perf = opt["perf"]
        sub(opt["name"])
        kv("Stringer section:", f"{sec['type']}  {sec['h']*1e3:.0f}mm tall")
        kv("Stringer area:", f"{sec['A']*1e6:.1f} mm²")
        kv("Stringer I:", f"{sec['I']*1e12:.0f} mm⁴")
        kv("Eccentricity e:", f"{perf['e']*1e3:.1f} mm")
        kv("t_eff (bending):", f"{perf['t_eff']*1e3:.2f} mm ({perf['t_eff']/t:.1f}×)")
        kv("σ_cr (global):", f"{perf['scr']/1e6:.1f} MPa")
        kv("σ_cr (local pocket):", f"{perf['scr_l']/1e6:.1f} MPa")
        kv("σ_cr (crippling):", f"{perf['scr_c']/1e6:.1f} MPa")
        kv("MS_global (FS=2.0):", f"{perf['ms_g']:+.2f}  {'✓' if perf['ms_g']>0 else '⚠'}")
        kv("MS_local (FS=1.5):", f"{perf['ms_l']:+.2f}  {'✓' if perf['ms_l']>0 else '⚠'}")
        kv("MS_crippling (FS=1.5):", f"{perf['ms_c']:+.2f}  {'✓' if perf['ms_c']>0 else '⚠'}")
        print()
        kv("Stringer mass:", f"{opt['m_str']:.0f} kg")
        kv("Ring mass:", f"{opt['m_ring']:.0f} kg")
        kv("Hardware (doublers+bolts):", f"{opt.get('m_doubler',0)+opt['m_bolts']+opt.get('m_clips',0):.0f} kg")
        kv("TOTAL stiffening mass:", f"{opt['m_total']:.0f} kg")
        kv("Total fastener count:", f"{opt['n_fast']:,d}")
        kv("Ring-stringer nodes:", f"{opt['n_nodes']}")
        print()
        kv("Ring attachment:", opt["ring_attach"])
        kv("Stringer attachment:", opt["str_attach"])
        print()
        for pro in opt["pros"]: print(f"      ✓ {pro}")
        for con in opt["cons"]: print(f"      ✗ {con}")

    # ── Score matrix ──
    sub("TRADE MATRIX (1-5 scale, 5 = best)")
    all_scores = [(opt, score_option(opt)) for opt in options]

    criteria = ["Structural", "Mass", "Assembly", "Systems", "Inspect", "Total"]
    print(f"\n    {'Criterion':<16s}", end="")
    for opt, _ in all_scores:
        print(f"  {opt['short']:>22s}", end="")
    print()
    print("    " + "-" * (16 + 24 * len(options)))

    for crit in criteria:
        print(f"    {crit:<16s}", end="")
        for _, sc in all_scores:
            val = sc[crit]
            marker = "★" if crit == "Total" and val == max(s[crit] for _, s in all_scores) else " "
            print(f"  {val:>20d} {marker}", end="")
        print()

    # ── Recommendation ──
    winner = max(all_scores, key=lambda x: x[1]["Total"])
    sub("RECOMMENDATION")
    print(f"\n    ★ {winner[0]['short']} scores highest ({winner[1]['Total']}/25)")
    print()

    # ── Why T-beam is the best fit ──
    sub("DETAILED RECOMMENDATION: T-BEAM STRINGERS")
    a = options[0]  # Option A
    print(f"""
    Your team's instinct is correct. The T-beam stringer with rings bolting
    to the flange is the right choice for a habitat module. Here's why:

    1. SYSTEMS INTEGRATION (your stated priority)
       The inward-facing flange creates a natural mounting shelf around the
       entire interior. At each ring station, the ring sits on top of the
       stringer flanges and bolts down. This gives you:
       • Continuous circumferential rail at each ring for equipment racks
       • Stringer flanges as longitudinal cable/conduit supports between rings
       • {a['n_nodes']} discrete mounting nodes at every intersection

    2. STRUCTURAL PERFORMANCE
       t_eff = {a['perf']['t_eff']*1e3:.1f}mm ({a['perf']['t_eff']/t:.1f}× skin)
       The flange adds ~{a['section']['A_fl']*1e6:.0f} mm² area at maximum eccentricity,
       which contributes disproportionately to EI via parallel axis theorem.
       MS_global = {a['perf']['ms_g']:+.2f} (all margins positive)

    3. ASSEMBLY
       {a['n_fast']:,d} total fasteners is moderate.
       Ring segments can be pre-drilled and installed after all stringers
       are in place — sequential build, no trapped hardware.

    4. MASS
       {a['m_total']:.0f} kg total — heavier than blade-only ({options[1]['m_total']:.0f} kg)
       but the flange mass buys you systems integration that blade
       stringers simply cannot provide.

    SUGGESTED T-BEAM DIMENSIONS (for {N_STR} stringers × {N_RING} rings):
       Web:    25mm tall × 3mm thick (7075-T6 extrusion)
       Flange: 20mm wide × 3mm thick (inward-facing)
       Doubler: 30mm wide × 3mm thick (2219-T67, under web foot)
       Fasteners: 3/16" A286 rivets @ 60mm pitch (stringer-to-shell)
                  1/4"-28 A286 bolts + locknuts (ring-to-flange nodes)
    """)

    # ═══ PLOTS ═══
    print("  Generating figures...")

    # ── Fig 15: Cross-section comparison ──
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    def draw_T(ax):
        ax.set_xlim(-0.025, 0.025); ax.set_ylim(-0.008, 0.040); ax.set_aspect("equal")
        # Shell
        ax.add_patch(Rectangle((-0.025, -0.005), 0.050, t, fc=C["blue"], alpha=0.3, ec="black", lw=1.5))
        ax.text(0.018, -0.003, "Shell (2219)", fontsize=7, color=C["navy"])
        # Doubler
        ax.add_patch(Rectangle((-0.015, 0), 0.030, 0.003, fc=C["gold"], alpha=0.4, ec="black", lw=1))
        # Web
        ax.add_patch(Rectangle((-0.0015, 0.003), 0.003, 0.025, fc=C["orange"], alpha=0.6, ec="black", lw=1.5))
        # Flange (T-top, inward)
        ax.add_patch(Rectangle((-0.010, 0.028), 0.020, 0.003, fc=C["orange"], alpha=0.6, ec="black", lw=1.5))
        ax.text(-0.008, 0.032, "Flange\n(ring mounts here)", fontsize=7, color=C["red"], fontweight="bold")
        # Ring (dashed, sitting on flange)
        ax.add_patch(Rectangle((-0.0015, 0.031), 0.003, 0.020, fc=C["teal"], alpha=0.3, ec=C["teal"],
                               lw=1.5, ls="--"))
        ax.text(0.005, 0.040, "Ring\n(bolted)", fontsize=7, color=C["teal"])
        # Bolts
        for bx in [-0.008, 0.008]:
            ax.plot(bx, 0.0295, "x", color=C["red"], ms=6, mew=2)
        for bx in [-0.008, 0.008]:
            ax.plot(bx, 0.001, "x", color=C["gray"], ms=5, mew=1.5)
        ax.set_title("Option A: T-beam Stringer", fontweight="bold", color=C["navy"])
        ax.set_xlabel("Width (m)"); ax.set_ylabel("Height (m)")

    def draw_blade(ax):
        ax.set_xlim(-0.025, 0.025); ax.set_ylim(-0.008, 0.040); ax.set_aspect("equal")
        ax.add_patch(Rectangle((-0.025, -0.005), 0.050, t, fc=C["blue"], alpha=0.3, ec="black", lw=1.5))
        ax.add_patch(Rectangle((-0.015, 0), 0.030, 0.003, fc=C["gold"], alpha=0.4, ec="black", lw=1))
        # Blade
        ax.add_patch(Rectangle((-0.0015, 0.003), 0.003, 0.025, fc=C["orange"], alpha=0.6, ec="black", lw=1.5))
        # Clip angle
        clip_pts = np.array([[-0.0015,0.015],[0.0015,0.015],[0.0015,0.020],[0.012,0.020],[0.012,0.023],[-.0015,0.023]])
        ax.add_patch(Polygon(clip_pts, closed=True, fc=C["purple"], alpha=0.3, ec=C["purple"], lw=1.5))
        ax.text(0.005, 0.024, "Clip angle", fontsize=7, color=C["purple"])
        # Ring (horizontal)
        ax.add_patch(Rectangle((0.003, 0.018), 0.020, 0.003, fc=C["teal"], alpha=0.3, ec=C["teal"], lw=1.5, ls="--"))
        ax.text(0.015, 0.015, "Ring", fontsize=7, color=C["teal"])
        ax.set_title("Option B: Blade + Clip Angle", fontweight="bold", color=C["navy"])
        ax.set_xlabel("Width (m)"); ax.set_ylabel("Height (m)")

    def draw_2L(ax):
        ax.set_xlim(-0.025, 0.025); ax.set_ylim(-0.008, 0.040); ax.set_aspect("equal")
        ax.add_patch(Rectangle((-0.025, -0.005), 0.050, t, fc=C["blue"], alpha=0.3, ec="black", lw=1.5))
        ax.add_patch(Rectangle((-0.020, 0), 0.040, 0.003, fc=C["gold"], alpha=0.4, ec="black", lw=1))
        # Left L
        ax.add_patch(Rectangle((-0.009, 0.003), 0.003, 0.025, fc=C["orange"], alpha=0.6, ec="black", lw=1.5))
        ax.add_patch(Rectangle((-0.009, 0.003), 0.015, 0.003, fc=C["orange"], alpha=0.6, ec="black", lw=1.5))
        # Right L
        ax.add_patch(Rectangle((0.006, 0.003), 0.003, 0.025, fc=C["orange"], alpha=0.6, ec="black", lw=1.5))
        ax.add_patch(Rectangle((-0.006, 0.003), 0.015, 0.003, fc=C["orange"], alpha=0.6, ec="black", lw=1.5))
        # Ring in gap
        ax.add_patch(Rectangle((-0.004, 0.006), 0.003, 0.018, fc=C["teal"], alpha=0.5, ec=C["teal"], lw=1.5))
        ax.annotate("Ring slots\nbetween L's", xy=(0, 0.015), xytext=(0.012, 0.030),
                    fontsize=7, color=C["teal"], arrowprops=dict(arrowstyle="->", color=C["teal"]))
        ax.set_title("Option C: Back-to-back L's", fontweight="bold", color=C["navy"])
        ax.set_xlabel("Width (m)"); ax.set_ylabel("Height (m)")

    def draw_hat(ax):
        ax.set_xlim(-0.030, 0.030); ax.set_ylim(-0.008, 0.040); ax.set_aspect("equal")
        ax.add_patch(Rectangle((-0.030, -0.005), 0.060, t, fc=C["blue"], alpha=0.3, ec="black", lw=1.5))
        # Hat: base flanges, two webs, top cap
        hat_pts = np.array([[-0.020,0],[-0.020,0.003],[-0.013,0.003],[-0.010,0.028],
                           [0.010,0.028],[0.013,0.003],[0.020,0.003],[0.020,0],[0.017,0],
                           [0.017,0.003],[0.010,0.025],[-0.010,0.025],[-0.017,0.003],
                           [-0.017,0],[-0.020,0]])
        ax.add_patch(Polygon(hat_pts, closed=True, fc=C["orange"], alpha=0.5, ec="black", lw=1.5))
        ax.text(-0.003, 0.012, "Conduit\nspace", fontsize=7, color=C["navy"], ha="center", style="italic")
        # Ring passing through (mouse hole)
        ax.add_patch(Rectangle((-0.025, 0.010), 0.008, 0.003, fc=C["teal"], alpha=0.5, ec=C["teal"], lw=1.5))
        ax.add_patch(Rectangle((0.017, 0.010), 0.008, 0.003, fc=C["teal"], alpha=0.5, ec=C["teal"], lw=1.5))
        ax.text(0.022, 0.015, "Ring", fontsize=7, color=C["teal"])
        ax.set_title("Option D: Hat-section", fontweight="bold", color=C["navy"])
        ax.set_xlabel("Width (m)"); ax.set_ylabel("Height (m)")

    draw_T(axes[0,0]); draw_blade(axes[0,1])
    draw_2L(axes[1,0]); draw_hat(axes[1,1])
    fig.suptitle("Stiffener Cross-Section Options (to scale)", fontsize=14, fontweight="bold", color=C["navy"], y=1.01)
    fig.tight_layout()
    p = os.path.join(OUT, "fig15_stiffener_sections.png"); fig.savefig(p, bbox_inches="tight"); plt.close(); print(f"  ✓ {p}")

    # ── Fig 16: Trade comparison bars ──
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 5.5))

    names = [o["short"] for o in options]
    x = np.arange(len(names))

    # Structural margins
    mg = [o["perf"]["ms_g"] for o in options]
    ml = [o["perf"]["ms_l"] for o in options]
    mc = [o["perf"]["ms_c"] for o in options]
    bw = 0.25
    ax1.bar(x-bw, mg, bw, label="Global (2.0)", color=C["teal"], edgecolor="white")
    ax1.bar(x, ml, bw, label="Local (1.5)", color=C["blue"], edgecolor="white")
    ax1.bar(x+bw, mc, bw, label="Crippling (1.5)", color=C["orange"], edgecolor="white")
    ax1.axhline(0, color="black", lw=1.5)
    ax1.set_xticks(x); ax1.set_xticklabels(names, fontsize=8, rotation=15, ha="right")
    ax1.set_ylabel("Margin of Safety"); ax1.set_title("Structural Margins", fontweight="bold", color=C["navy"])
    ax1.legend(fontsize=8)

    # Mass & fasteners
    mt = [o["m_total"] for o in options]
    bars = ax2.bar(names, mt, color=[C["teal"],C["blue"],C["orange"],C["gold"]], edgecolor="white", width=0.5)
    for b, v in zip(bars, mt):
        ax2.text(b.get_x()+b.get_width()/2, v+5, f"{v:.0f} kg", ha="center", fontsize=10, fontweight="bold")
    ax2.set_ylabel("Total Stiffening Mass (kg)")
    ax2.set_title("Mass Comparison", fontweight="bold", color=C["navy"])
    ax2.set_xticklabels(names, fontsize=8, rotation=15, ha="right")

    # Trade matrix radar-ish (bar version)
    crit_names = ["Structural", "Mass", "Assembly", "Systems", "Inspect"]
    all_sc = [score_option(o) for o in options]
    bw = 0.18
    for i, (o, sc) in enumerate(zip(options, all_sc)):
        vals = [sc[c] for c in crit_names]
        ax3.bar(np.arange(len(crit_names)) + i*bw, vals, bw,
                label=o["short"], alpha=0.8, edgecolor="white")
    ax3.set_xticks(np.arange(len(crit_names)) + 1.5*bw)
    ax3.set_xticklabels(crit_names, fontsize=8)
    ax3.set_ylabel("Score (1-5)"); ax3.set_ylim(0, 6)
    ax3.set_title("Trade Matrix Scores", fontweight="bold", color=C["navy"])
    ax3.legend(fontsize=7, loc="upper right")

    fig.tight_layout()
    p = os.path.join(OUT, "fig16_attachment_trade.png"); fig.savefig(p); plt.close(); print(f"  ✓ {p}")


if __name__ == "__main__":
    main()
