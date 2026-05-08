### ============================================================
### GHOST INTERFEROMETER: THE PHANTOM FORCE TEST
### AC Stark Shift (Dispersive ZZ Coupling) Asymmetry
### ============================================================

import json
import math
import numpy as np
from qiskit import QuantumCircuit
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

### ============================================================
### EXPERIMENT CONFIGURATION
### ============================================================
EXECUTION_MODE = "CLOUD"

MY_TOKEN = "YOUR_TOKEN_HERE"
MY_CRN = "YOUR_CRN_HERE" # Get this from the 'Instances' tab on quantum.cloud.ibm.com

NUM_SHOTS = 4096
PHI_TARGET = 3.311

# Sweeping the Dispersive Coupling Strength (Phase accumulation in radians)
# We test very weak interactions to prevent complete decoherence
STARK_SHIFTS = [0.05, 0.10, 0.15, 0.20, 0.25]

if EXECUTION_MODE == "LOCAL":
    print("Initializing LOCAL simulator environment...")
    from qiskit_ibm_runtime.fake_provider import FakeLimaV2
    backend = FakeLimaV2()
else:
    print("Authenticating with IBM Quantum Platform...")
    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=MY_TOKEN, instance=MY_CRN)
    print("Scanning for the least busy operational quantum processor...")
    backend = service.least_busy(operational=True, simulator=False)

print(f"Target Backend: {backend.name} | Phase: {PHI_TARGET} rad")
print(f"AC Stark Shift sweeps: {STARK_SHIFTS} rad")
print(f"Total iterations: {NUM_SHOTS * 4 * len(STARK_SHIFTS)} (4 control quadrants per shift)")

### ============================================================
### LOGICAL-TO-PHYSICAL MAPPING DICTIONARY
### measure([1, 2], [0, 1]) -> c0=q1, c1=q2.
### String index 0 is c1 (q2). String index 1 is c0 (q1).
### ============================================================
mapping = {
    "std_fwd":  {"A": 1, "B": 0},
    "std_rev":  {"A": 1, "B": 0},
    "swap_fwd": {"A": 0, "B": 1},
    "swap_rev": {"A": 0, "B": 1}
}

### ============================================================
### CIRCUIT CONSTRUCTION: THE DISPERSIVE PHASE SENSORS
### ============================================================
circuits = []
results_keys = []

for theta in STARK_SHIFTS:
    # --------------------------------------------------------------
    # 1. STD-FORWARD: Sensor A (q1) precedes Sensor B (q2)
    # --------------------------------------------------------------
    qc_std_fwd = QuantumCircuit(4, 2, name=f"std_fwd_th{theta:.2f}")
    qc_std_fwd.h(0) # Particle entering interferometer
    qc_std_fwd.h(1) # Sensor A ("Vela") prepared in X-basis
    qc_std_fwd.h(2) # Sensor B ("Vela") prepared in X-basis
    
    qc_std_fwd.barrier()
    qc_std_fwd.cp(theta, 0, 1) # Dispersive ZZ coupling (AC Stark) on Path A
    qc_std_fwd.barrier()
    
    qc_std_fwd.rz(PHI_TARGET, 0)
    
    qc_std_fwd.barrier()
    qc_std_fwd.x(0)
    qc_std_fwd.cp(theta, 0, 2) # Dispersive ZZ coupling (AC Stark) on Path B
    qc_std_fwd.x(0)
    qc_std_fwd.barrier()
    
    qc_std_fwd.h(0) # Close particle interferometer
    qc_std_fwd.h(1) # Map accumulated phase to population on Sensor A
    qc_std_fwd.h(2) # Map accumulated phase to population on Sensor B
    qc_std_fwd.measure([1, 2], [0, 1])
    circuits.append(qc_std_fwd)

    # --------------------------------------------------------------
    # 2. STD-REVERSE: Sensor B (q2) precedes Sensor A (q1)
    # --------------------------------------------------------------
    qc_std_rev = QuantumCircuit(4, 2, name=f"std_rev_th{theta:.2f}")
    qc_std_rev.h([0, 1, 2])
    qc_std_rev.barrier()
    qc_std_rev.x(0)
    qc_std_rev.cp(theta, 0, 2)
    qc_std_rev.x(0)
    qc_std_rev.barrier()
    qc_std_rev.rz(PHI_TARGET, 0)
    qc_std_rev.barrier()
    qc_std_rev.cp(theta, 0, 1)
    qc_std_rev.barrier()
    qc_std_rev.h([0, 1, 2])
    qc_std_rev.measure([1, 2], [0, 1])
    circuits.append(qc_std_rev)

    # --------------------------------------------------------------
    # 3. SWAP-FORWARD: Sensor A (q2) precedes Sensor B (q1)
    # --------------------------------------------------------------
    qc_swap_fwd = QuantumCircuit(4, 2, name=f"swap_fwd_th{theta:.2f}")
    qc_swap_fwd.h([0, 1, 2])
    qc_swap_fwd.barrier()
    qc_swap_fwd.cp(theta, 0, 2)
    qc_swap_fwd.barrier()
    qc_swap_fwd.rz(PHI_TARGET, 0)
    qc_swap_fwd.barrier()
    qc_swap_fwd.x(0)
    qc_swap_fwd.cp(theta, 0, 1)
    qc_swap_fwd.x(0)
    qc_swap_fwd.barrier()
    qc_swap_fwd.h([0, 1, 2])
    qc_swap_fwd.measure([1, 2], [0, 1])
    circuits.append(qc_swap_fwd)

    # --------------------------------------------------------------
    # 4. SWAP-REVERSE: Sensor B (q1) precedes Sensor A (q2)
    # --------------------------------------------------------------
    qc_swap_rev = QuantumCircuit(4, 2, name=f"swap_rev_th{theta:.2f}")
    qc_swap_rev.h([0, 1, 2])
    qc_swap_rev.barrier()
    qc_swap_rev.x(0)
    qc_swap_rev.cp(theta, 0, 1)
    qc_swap_rev.x(0)
    qc_swap_rev.barrier()
    qc_swap_rev.rz(PHI_TARGET, 0)
    qc_swap_rev.barrier()
    qc_swap_rev.cp(theta, 0, 2)
    qc_swap_rev.barrier()
    qc_swap_rev.h([0, 1, 2])
    qc_swap_rev.measure([1, 2], [0, 1])
    circuits.append(qc_swap_rev)
    
    results_keys.append(f"theta_{theta:.2f}")

### ============================================================
### TRANSPILATION & EXECUTION
### ============================================================
pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
optimized_circuits = pm.run(circuits)

sampler = Sampler(mode=backend)
sampler.options.default_shots = NUM_SHOTS

print(f"\nSubmitting Phantom Force sequence to processor {backend.name}...")
job = sampler.run(optimized_circuits)
print(f"Job ID: {job.job_id()} - Awaiting dispersive execution...")

result = job.result()

### ============================================================
### DATA EXTRACTION & ANALYSIS
### ============================================================
data = {}
print("\n--- AC STARK SHIFT ASYMMETRY RESULTS ---")

for i, theta in enumerate(STARK_SHIFTS):
    idx_base = i * 4
    
    asyms = []
    errs = []
    
    for j, direction in enumerate(["std_fwd", "std_rev", "swap_fwd", "swap_rev"]):
        c = result[idx_base + j].data.c.get_counts()
        name = f"{direction}_th{theta:.2f}"
        data[name] = c
        
        idx_A = mapping[direction]["A"]
        idx_B = mapping[direction]["B"]
        
        # Sensor registers a phase shift by falling into |1> after the final H gate
        sens_a = sum(count for state, count in c.items() if state[idx_A] == '1')
        sens_b = sum(count for state, count in c.items() if state[idx_B] == '1')
        
        asym = sens_a - sens_b
        err = math.sqrt(sens_a + sens_b)
        
        asyms.append(asym)
        errs.append(err)

    # Calculate absolute physical signal removing spatial and temporal bias
    delta_phys_std = (asyms[0] + asyms[1]) / 2
    delta_phys_swap = (asyms[2] + asyms[3]) / 2
    true_physics_signal = (delta_phys_std + delta_phys_swap) / 2
    
    variance_sum = sum(e**2 for e in errs)
    true_physics_err = math.sqrt(variance_sum) / 4
    sigma = true_physics_signal / true_physics_err if true_physics_err > 0 else 0
    
    print(f"\nStark Shift: {theta:.2f} rad")
    print(f"  Physical Asymmetry Signal: {true_physics_signal:+.2f} ± {true_physics_err:.2f} counts")
    print(f"  Statistical Significance:  {sigma:+.2f}σ")

with open("phantom_force_results.json", "w") as f:
    json.dump(data, f, indent=4)

print("\nData exported to phantom_force_results.json.")
