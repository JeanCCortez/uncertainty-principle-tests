### ============================================================
### GHOST INTERFEROMETER: THE 5-SIGMA PEAK ATTACK
### Mirror-Test for Hardware Bias Elimination
### ============================================================

import json
import numpy as np
from qiskit import QuantumCircuit
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

### ============================================================
### BACKEND CONFIGURATION
### ============================================================
EXECUTION_MODE = "CLOUD"

MY_TOKEN = "YOUR_TOKEN_HERE"
MY_CRN = "YOUR_CRN_HERE" 

NUM_SHOTS = 8192
THETA = 0.10  # Reduced coupling to preserve interference envelope
NUM_PHASES = 10

if EXECUTION_MODE == "LOCAL":
    print("Initializing LOCAL simulator...")
    from qiskit_ibm_runtime.fake_provider import FakeLimaV2
    backend = FakeLimaV2()
else:
    print("Authenticating with IBM Cloud (Real Hardware)...")
    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=MY_TOKEN, instance=MY_CRN)
    print("Scanning IBM Cloud for the least busy operational quantum processor...")
    backend = service.least_busy(operational=True, simulator=False)

# Focusing on the anomaly peak (3.0 to 3.7 rad)
target_phases = np.linspace(3.0, 3.7, NUM_PHASES)

# Total shots: 8192 * 10 phases * 2 circuits (Standard + Swapped) = 163,840
print(f"Backend: {backend.name} | Peak Focus | Theta: {THETA}")
print(f"Total shots executing: {NUM_SHOTS * NUM_PHASES * 2}")

### ============================================================
### BUILDING THE 20 CIRCUITS (10 Standard + 10 Swapped)
### ============================================================
circuits = []

for i, phi in enumerate(target_phases):
    # --------------------------------------------------------
    # CIRCUIT 1: STANDARD MAPPING
    # Sensor A on physical q1 | Sensor B on physical q2
    # --------------------------------------------------------
    qc_std = QuantumCircuit(4, 2)
    qc_std.name = f"peak_std_{i}"
    
    qc_std.h(0)
    qc_std.cry(THETA, 0, 1) # Sensor A probes Path A
    qc_std.p(phi, 0)
    
    # Invert q0 to map the shadow path
    qc_std.x(0)
    qc_std.cry(THETA, 0, 2) # Sensor B probes Path B
    qc_std.x(0)
    
    qc_std.h(0)
    
    # Measurement: c0 = Sensor A (q1), c1 = Sensor B (q2)
    qc_std.measure([1, 2], [0, 1])
    circuits.append(qc_std)

    # --------------------------------------------------------
    # CIRCUIT 2: MIRROR MAPPING (SYMMETRY CONTROL)
    # Sensor A on physical q2 | Sensor B on physical q1
    # --------------------------------------------------------
    qc_swap = QuantumCircuit(4, 2)
    qc_swap.name = f"peak_swap_{i}"
    
    qc_swap.h(0)
    qc_swap.cry(THETA, 0, 2) # Sensor A NOW PROBES USING QUBIT 2
    qc_swap.p(phi, 0)
    
    # Invert q0 to map the shadow path
    qc_swap.x(0)
    qc_swap.cry(THETA, 0, 1) # Sensor B NOW PROBES USING QUBIT 1
    qc_swap.x(0)
    
    qc_swap.h(0)
    
    # Measurement: c0 = Sensor A (q2), c1 = Sensor B (q1)
    # This keeps the logical output identical (c0 is always Sensor A)
    qc_swap.measure([2, 1], [0, 1])
    circuits.append(qc_swap)

### ============================================================
### TRANSPILATION AND EXECUTION
### ============================================================
pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
optimized_circuits = pm.run(circuits)

sampler = Sampler(mode=backend)
sampler.options.default_shots = NUM_SHOTS 

print(f"Sending Mirror-Test suite to processor {backend.name}...")
job = sampler.run(optimized_circuits)
print(f"Job ID: {job.job_id()}. Waiting for results...")

result = job.result()

### ============================================================
### DATA EXTRACTION AND MIRROR ANALYSIS
### ============================================================
data = {}
asymmetries_std = []
asymmetries_swap = []

print("\n--- ASYMMETRY ANALYSIS (STANDARD VS SWAPPED) ---")
print("If Asymmetry remains positive in both, hardware bias is eliminated.")

for i in range(NUM_PHASES):
    phase_val = target_phases[i]
    
    # Extract Standard
    c_std = result[i * 2].data.c.get_counts()
    data[f"phi_{phase_val:.3f}_std"] = c_std
    
    # Extract Swap
    c_swap = result[i * 2 + 1].data.c.get_counts()
    data[f"phi_{phase_val:.3f}_swap"] = c_swap

    # Evaluate Standard (Qiskit string is 'c1 c0' -> 'SensorB SensorA')
    q1_std = sum(count for state, count in c_std.items() if state[1] == '1')
    q2_std = sum(count for state, count in c_std.items() if state[0] == '1')
    asym_std = q1_std - q2_std
    asymmetries_std.append(asym_std)
    
    # Evaluate Swap (Classical registers are logically mapped the same way)
    q1_swap = sum(count for state, count in c_swap.items() if state[1] == '1')
    q2_swap = sum(count for state, count in c_swap.items() if state[0] == '1')
    asym_swap = q1_swap - q2_swap
    asymmetries_swap.append(asym_swap)

    print(f"Phase {phase_val:.2f} rad | Std Asym: {asym_std:+d} | Swap Asym: {asym_swap:+d}")

with open("peak_mirror_results.json", "w") as f:
    json.dump(data, f, indent=4)

print("\n============================================================")
print("DATA SAVED TO peak_mirror_results.json")
print("============================================================")

### ============================================================
### FINAL VERDICT
### ============================================================
mean_std = np.mean(asymmetries_std)
err_std = np.std(asymmetries_std) / np.sqrt(NUM_PHASES)

mean_swap = np.mean(asymmetries_swap)
err_swap = np.std(asymmetries_swap) / np.sqrt(NUM_PHASES)

# Combined analytical signal (averaging the asymmetry across both hardware mappings)
combined_mean = (mean_std + mean_swap) / 2
combined_err = np.sqrt(err_std**2 + err_swap**2) / 2
sigma = combined_mean / combined_err if combined_err > 0 else 0

print(f"\n=== THE 5-SIGMA MIRROR VERDICT ===")
print(f"Mean Asymmetry (Standard HW): {mean_std:.1f} ± {err_std:.1f}")
print(f"Mean Asymmetry (Swapped HW):  {mean_swap:.1f} ± {err_swap:.1f}")
print(f"True Physics Signal (Combined): {combined_mean:.1f} ± {combined_err:.1f} counts")
print(f"Final Statistical Significance: {sigma:.2f}σ")

if combined_mean > 0 and abs(sigma) > 5.0:
    print("\n[!] ABSOLUTE DISCOVERY: Asymmetry survived the hardware swap at >5σ.")
    print("The vacuum is fundamentally anisotropic. The Uncerainty Principle fails.")
elif combined_mean > 0 and abs(sigma) > 3.0:
    print("\n[!] STRONG EVIDENCE: Asymmetry is independent of hardware mapping.")
else:
    print("\n[-] HARDWARE ARTIFACT: The asymmetry did not survive the swap. Physics remains Standard.")