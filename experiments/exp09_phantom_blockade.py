### ============================================================
### GHOST INTERFEROMETER: THE PHANTOM BLOCKADE TEST
### Mid-Circuit Macroscopic Measurement & Post-Selection
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

print(f"Target Backend: {backend.name} (Dynamic Circuits Enabled)")
print(f"Executing Phase Sweep: {NUM_PHASES} points from 0 to 2*pi")
print(f"Total Shots: {NUM_SHOTS * NUM_PHASES}")

### ============================================================
### CIRCUIT CONSTRUCTION: MID-CIRCUIT MACROSCOPIC BLOCKADE
### q0: Particle | q1: Blockade Detector
### ============================================================
circuits = []

for phi in PHASES:
    qc = QuantumCircuit(2, 2, name=f"blockade_phi_{phi:.3f}")
    
    # 1. Enter Interferometer (Superposition of paths)
    qc.h(0)
    qc.barrier()
    
    # 2. Entangle Blockade Detector to Path |1>
    qc.cx(0, 1)
    
    # 3. THE PHANTOM BLOCKADE (Mid-Circuit Measurement)
    # This triggers the microwave readout resonators in real-time.
    # It is a macroscopic, non-unitary thermodynamic interaction.
    qc.measure(1, 1) 
    
    qc.barrier()
    
    # 4. Phase Shift on Particle (Sweeping the interference fringe)
    qc.rz(phi, 0)
    qc.barrier()
    
    # 5. Close Interferometer
    qc.h(0)
    
    # 6. Final Measurement of the Particle
    # c0 = Particle (q0), c1 = Blockade Record (q1)
    qc.measure(0, 0)
    
    circuits.append(qc)

### ============================================================
### TRANSPILATION & EXECUTION
### ============================================================
pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
optimized_circuits = pm.run(circuits)

sampler = Sampler(mode=backend)
sampler.options.default_shots = NUM_SHOTS

print(f"\nSubmitting Phantom Blockade sequence to {backend.name}...")
job = sampler.run(optimized_circuits)
print(f"Job ID: {job.job_id()} - Awaiting dynamic execution...")

result = job.result()

### ============================================================
### DATA EXTRACTION & POST-SELECTION ANALYSIS
### ============================================================
data = {}
print("\n--- PHANTOM BLOCKADE RESULTS ---")
print("Analyzing exclusively the events where the Particle SURVIVED the Blockade (q1 = 0).")

post_selected_probs = []
surviving_shots_list = []

for i, phi in enumerate(PHASES):
    c = result[i].data.c.get_counts()
    data[f"phi_{phi:.3f}"] = c
    
    # Qiskit outputs "c1 c0" -> c1 is Blockade (Index 0), c0 is Particle (Index 1)
    # We only care about cases where c1 == '0' (Blockade found nothing)
    survived_0 = c.get("00", 0) # Blockade=0, Particle=0
    survived_1 = c.get("01", 0) # Blockade=0, Particle=1
    
    total_survived = survived_0 + survived_1
    surviving_shots_list.append(total_survived)
    
    if total_survived > 0:
        p0_survived = survived_0 / total_survived
    else:
        p0_survived = 0.5
        
    post_selected_probs.append(p0_survived)
    
    print(f"Phi {phi:.2f} rad | Surviving Shots: {total_survived:4d} | P(Particle=0 | Blockade=0): {p0_survived:.4f}")

with open("phantom_blockade_results.json", "w") as f:
    json.dump(data, f, indent=4)

### ============================================================
### THEORETICAL VERDICT
### ============================================================
# Calculate the visibility of the interference fringe in the surviving subset
max_p = max(post_selected_probs)
min_p = min(post_selected_probs)
visibility = (max_p - min_p) / (max_p + min_p) if (max_p + min_p) > 0 else 0

avg_surviving = sum(surviving_shots_list) / len(surviving_shots_list)

print("\n=== THE BLOCKADE VERDICT ===")
print(f"Average Surviving Shots per phase: {avg_surviving:.0f} (Expected ~{NUM_SHOTS/2:.0f})")
print(f"Residual Interference Visibility: {visibility:.4f}")

if visibility > 0.2:
    print("\n[!] ABSOLUTE DISCOVERY: Interference survived the macroscopic null-measurement.")
    print("The empty wave bypassed the readout resonator and maintained coherence.")
    print("The particle never traversed the blocked path, falsifying non-local collapse.")
else:
    print("\n[-] COPENHAGEN CONFIRMED: The macroscopic null-measurement destroyed the wave.")
    print("Measuring 'nothing' on Path |1> was sufficient to instantly collapse Path |0>.")
    print("The pilot wave does not survive macroscopic thermodynamic decoupling.")