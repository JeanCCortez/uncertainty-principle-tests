### ============================================================
### GHOST INTERFEROMETER: INTERACTION-FREE MEASUREMENT TEST
### Path-Witness Entanglement and Visibility Analysis
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

MY_TOKEN = "KwgGZ3CMazqSPiRTF7gBgoENRS4SbCqcy7C_fIdbqd1-"
MY_CRN = "crn:v1:bluemix:public:quantum-computing:us-east:a/2751423f3df54bf9b963caabf1ceb7e4:e61c405d-5568-4f6b-97dd-0733e1af0fa3::" 

NUM_SHOTS = 8192
NUM_PHASES = 15
PHASES = np.linspace(0, 2 * np.pi, NUM_PHASES)

if EXECUTION_MODE == "LOCAL":
    print("Initializing LOCAL simulator environment...")
    from qiskit_ibm_runtime.fake_provider import FakeLimaV2
    backend = FakeLimaV2()
else:
    print("Authenticating with IBM Quantum Platform...")
    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=MY_TOKEN, instance=MY_CRN)
    print("Scanning for the least busy operational quantum processor...")
    backend = service.least_busy(operational=True, simulator=False)

print(f"Target Backend: {backend.name}")
print(f"Executing Phase Sweep: {NUM_PHASES} points from 0 to 2*pi")
print(f"Total Shots: {NUM_SHOTS * NUM_PHASES}")

### ============================================================
### CIRCUIT CONSTRUCTION: ENTANGLED PATH WITNESS
### q0: Particle | q1: Witness
### ============================================================
circuits = []

for phi in PHASES:
    qc = QuantumCircuit(2, 2, name=f"ifm_phi_{phi:.3f}")
    
    # 1. Enter Interferometer (Superposition of paths)
    qc.h(0)
    
    # 2. Entangle Witness (Interaction-Free Path Marker)
    # If q0 is in path |1>, q1 flips to |1>. If q0 is |0>, q1 stays |0>.
    qc.cx(0, 1)
    
    qc.barrier()
    
    # 3. Phase Shift on Particle (Sweeping the interference fringe)
    qc.rz(phi, 0)
    
    qc.barrier()
    
    # 4. Close Interferometer
    qc.h(0)
    
    # 5. Measure both. c0 = Particle (q0), c1 = Witness (q1)
    # Qiskit output string is "c1 c0" -> "Witness Particle"
    qc.measure([0, 1], [0, 1])
    
    circuits.append(qc)

### ============================================================
### TRANSPILATION & EXECUTION
### ============================================================
pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
optimized_circuits = pm.run(circuits)

sampler = Sampler(mode=backend)
sampler.options.default_shots = NUM_SHOTS

print(f"\nSubmitting Interaction-Free Measurement sequence to {backend.name}...")
job = sampler.run(optimized_circuits)
print(f"Job ID: {job.job_id()} - Awaiting physics execution...")

result = job.result()

### ============================================================
### DATA EXTRACTION & INTERFERENCE VISIBILITY ANALYSIS
### ============================================================
data = {}
print("\n--- INTERFERENCE VISIBILITY RESULTS ---")
print("Qiskit string format: 'Witness Particle'")

# Arrays to track the interference fringes
prob_q0_zero_total = []
prob_q0_zero_given_q1_zero = []
prob_q0_zero_given_q1_one = []

for i, phi in enumerate(PHASES):
    c = result[i].data.c.get_counts()
    data[f"phi_{phi:.3f}"] = c
    
    # Count occurrences (String: "c1 c0" -> "q1 q0")
    count_00 = c.get("00", 0)  # Witness=0, Particle=0
    count_01 = c.get("01", 0)  # Witness=0, Particle=1
    count_10 = c.get("10", 0)  # Witness=1, Particle=0
    count_11 = c.get("11", 0)  # Witness=1, Particle=1
    
    total = sum(c.values())
    
    # 1. Total unconditional probability of particle ending in state |0>
    p0_total = (count_00 + count_10) / total
    prob_q0_zero_total.append(p0_total)
    
    # 2. Post-selected probability of particle in |0> GIVEN witness is |0>
    p0_given_w0 = count_00 / (count_00 + count_01) if (count_00 + count_01) > 0 else 0
    prob_q0_zero_given_q1_zero.append(p0_given_w0)
    
    # 3. Post-selected probability of particle in |0> GIVEN witness is |1>
    p0_given_w1 = count_10 / (count_10 + count_11) if (count_10 + count_11) > 0 else 0
    prob_q0_zero_given_q1_one.append(p0_given_w1)

    print(f"Phi {phi:.2f} rad | P(Part=0): {p0_total:.3f} | P(Part=0|Wit=0): {p0_given_w0:.3f} | P(Part=0|Wit=1): {p0_given_w1:.3f}")

with open("interaction_free_results.json", "w") as f:
    json.dump(data, f, indent=4)

### ============================================================
### THEORETICAL VERDICT
### ============================================================
def calculate_visibility(probabilities):
    return (max(probabilities) - min(probabilities)) / (max(probabilities) + min(probabilities)) if max(probabilities) > 0 else 0

vis_total = calculate_visibility(prob_q0_zero_total)
vis_w0 = calculate_visibility(prob_q0_zero_given_q1_zero)

print("\n=== THEORETICAL VERDICT ===")
print(f"Total Unconditional Visibility: {vis_total:.3f}")
print(f"Post-Selected Visibility (Witness=0): {vis_w0:.3f}")

if vis_total > 0.2 or vis_w0 > 0.2:
    print("\n[!] EXTRAORDINARY DISCOVERY: Interference fringes survived the path-witness entanglement.")
    print("The particle's trajectory was known without interaction, and wave behavior persisted.")
    print("This falsifies the Copenhagen Complementarity Principle.")
else:
    print("\n[-] COPENHAGEN CONFIRMED: Visibility collapsed entirely (V ~ 0).")
    print("Entangling the path with the witness, even without direct secondary interaction,")
    print("was sufficient to completely destroy the particle's interference pattern.")