### ============================================================
### GHOST INTERFEROMETER: TEST 11
### Delayed-Choice Quantum Eraser (Wheeler's Delayed Choice)
### ============================================================

import json
import math
import numpy as np
from qiskit import QuantumCircuit
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

### ============================================================
### CONFIGURATION
### ============================================================
EXECUTION_MODE = "CLOUD"
MY_TOKEN = "KwgGZ3CMazqSPiRTF7gBgoENRS4SbCqcy7C_fIdbqd1-"
MY_CRN = "crn:v1:bluemix:public:quantum-computing:us-east:a/2751423f3df54bf9b963caabf1ceb7e4:e61c405d-5568-4f6b-97dd-0733e1af0fa3::" 

NUM_SHOTS = 8192
NUM_PHASES = 15
PHASES = np.linspace(0, 2 * np.pi, NUM_PHASES)

if EXECUTION_MODE == "LOCAL":
    from qiskit_ibm_runtime.fake_provider import FakeLimaV2
    backend = FakeLimaV2()
else:
    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=MY_TOKEN, instance=MY_CRN)
    backend = service.least_busy(operational=True, simulator=False)

print(f"Target Backend: {backend.name} (Dynamic Circuits Required)")
print(f"Executing Phase Sweep: {NUM_PHASES} points")
print(f"Total Shots per Circuit: {NUM_SHOTS}")

### ============================================================
### CIRCUIT CONSTRUCTION
### q0: Particle | q1: Path Marker | q2: Quantum Coin (RNG)
### ============================================================
circuits = []

for phi in PHASES:
    qc = QuantumCircuit(3, 3, name=f"dcqe_{phi:.3f}")
    
    # 1. Particle enters interferometer
    qc.h(0)
    qc.barrier()
    
    # 2. Path Marker gets entangled with Particle
    qc.cx(0, 1)
    qc.barrier()
    
    # 3. Phase Shift on Particle
    qc.rz(phi, 0)
    qc.barrier()
    
    # 4. Particle closes interferometer
    qc.h(0)
    
    # 5. MACROSCOPIC MEASUREMENT OF THE PARTICLE
    # Particle hits the screen BEFORE the choice to erase is made.
    qc.measure(0, 0)
    qc.barrier()
    
    # 6. DELAYED CHOICE (Quantum RNG)
    # Coin flip to decide if we erase or keep the path information
    qc.h(2)
    qc.measure(2, 2)
    
    # 7. THE ERASER
    # If coin (c2) == 1: Apply H to marker (Erase path info)
    # If coin (c2) == 0: Do nothing (Keep path info)
    with qc.if_test((qc.clbits[2], 1)):
        qc.h(1)
        
    # 8. Final measurement of the Marker
    qc.measure(1, 1)
    
    circuits.append(qc)

### ============================================================
### TRANSPILATION & EXECUTION
### ============================================================
pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
opt_circuits = pm.run(circuits)

sampler = Sampler(mode=backend)
sampler.options.default_shots = NUM_SHOTS

print(f"\nSubmitting Delayed-Choice Quantum Eraser to {backend.name}...")
job = sampler.run(opt_circuits)
print(f"Job ID: {job.job_id()} - Awaiting dynamic execution...")

result = job.result()

### ============================================================
### DATA EXTRACTION & ANALYSIS
### ============================================================
data = {}
print("\n--- DELAYED-CHOICE QUANTUM ERASER RESULTS ---")
print("Qiskit String Format: 'Coin(c2) Marker(c1) Particle(c0)'\n")

visibility_data = {
    "kept": [],          # Path Info Kept (Coin = 0)
    "erased_m0": [],     # Path Info Erased (Coin = 1), Marker = 0
    "erased_m1": []      # Path Info Erased (Coin = 1), Marker = 1
}

for i, phi in enumerate(PHASES):
    c = result[i].data.c.get_counts()
    data[f"phi_{phi:.3f}"] = c
    
    # --- Data Parsing ---
    # c2 (index 0) = RNG Coin: '0' (Keep), '1' (Erase)
    # c1 (index 1) = Marker: Path ID if kept, Eraser state if erased
    # c0 (index 2) = Particle: Interference measurement
    
    # 1. Path Kept (Coin == '0')
    kept_total = sum(count for state, count in c.items() if state[0] == '0')
    kept_p0 = sum(count for state, count in c.items() if state[0] == '0' and state[2] == '0')
    prob_kept_p0 = kept_p0 / kept_total if kept_total > 0 else 0.5
    visibility_data["kept"].append(prob_kept_p0)
    
    # 2. Path Erased (Coin == '1'), Sub-ensemble Marker == '0'
    erased_m0_total = sum(count for state, count in c.items() if state[0] == '1' and state[1] == '0')
    erased_m0_p0 = sum(count for state, count in c.items() if state[0] == '1' and state[1] == '0' and state[2] == '0')
    prob_erased_m0_p0 = erased_m0_p0 / erased_m0_total if erased_m0_total > 0 else 0.5
    visibility_data["erased_m0"].append(prob_erased_m0_p0)

    # 3. Path Erased (Coin == '1'), Sub-ensemble Marker == '1'
    erased_m1_total = sum(count for state, count in c.items() if state[0] == '1' and state[1] == '1')
    erased_m1_p0 = sum(count for state, count in c.items() if state[0] == '1' and state[1] == '1' and state[2] == '0')
    prob_erased_m1_p0 = erased_m1_p0 / erased_m1_total if erased_m1_total > 0 else 0.5
    visibility_data["erased_m1"].append(prob_erased_m1_p0)

    print(f"Phi {phi:.2f} rad | Kept P(|0>): {prob_kept_p0:.3f} | Erased(M0) P(|0>): {prob_erased_m0_p0:.3f} | Erased(M1) P(|0>): {prob_erased_m1_p0:.3f}")

with open("delayed_choice_results.json", "w") as f:
    json.dump(data, f, indent=4)

### ============================================================
### THEORETICAL VERDICT
### ============================================================
def calc_visibility(probs):
    return (max(probs) - min(probs)) / (max(probs) + min(probs)) if (max(probs) + min(probs)) > 0 else 0

vis_kept = calc_visibility(visibility_data["kept"])
vis_erased_m0 = calc_visibility(visibility_data["erased_m0"])
vis_erased_m1 = calc_visibility(visibility_data["erased_m1"])

print("\n=== THE DELAYED-CHOICE VERDICT ===")
print(f"Visibility (Path Known / Kept): {vis_kept:.4f}")
print(f"Visibility (Path Erased / M=0): {vis_erased_m0:.4f}")
print(f"Visibility (Path Erased / M=1): {vis_erased_m1:.4f}")

if vis_kept < 0.1 and (vis_erased_m0 > 0.3 or vis_erased_m1 > 0.3):
    print("\n[-] COPENHAGEN CONFIRMED: Retrocausal or non-local wave behavior observed.")
    print("The interference was recovered AFTER the particle had already hit the screen.")
    print("The pilot-wave trajectory is insufficient to explain this temporal paradox locally.")
elif vis_kept < 0.1 and vis_erased_m0 < 0.1 and vis_erased_m1 < 0.1:
    print("\n[?] DECOHERENCE LIMIT: Eraser failed to recover fringes.")
    print("Hardware noise may have irreversibly collapsed the state.")
else:
    print("\n[!] ANOMALY: Fringes persisted even when path information was explicitly kept.")
    print("This indicates a profound failure in the entangling protocol or the orthodox theory.")