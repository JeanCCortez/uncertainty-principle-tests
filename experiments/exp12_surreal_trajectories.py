### ============================================================
### GHOST INTERFEROMETER: TEST 12 - SURREAL TRAJECTORIES
### 3-Path Interferometer & Weak Trajectory Tracking
### ============================================================

import json
import math
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import RYGate
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

### ============================================================
### CONFIGURATION
### ============================================================
EXECUTION_MODE = "CLOUD"
MY_TOKEN = "YOUR_TOKEN_HERE"
MY_CRN = "YOUR_CRN_HERE" # Get this from the 'Instances' tab on quantum.cloud.ibm.com

NUM_SHOTS = 8192
THETA_W = 0.15  # Weak coupling strength
NUM_PHASES = 10
PHASES = np.linspace(0, 2 * np.pi, NUM_PHASES)

if EXECUTION_MODE == "LOCAL":
    from qiskit_ibm_runtime.fake_provider import FakeLimaV2
    backend = FakeLimaV2()
else:
    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=MY_TOKEN, instance=MY_CRN)
    backend = service.least_busy(operational=True, simulator=False)

### ============================================================
### 3-PATH INTERFEROMETER COMPONENTS
### System Qubits: q0, q1
### Path 1 = |00>, Path 2 = |10>, Path 3 = |11>
### ============================================================
def init_three_paths(qc, sys_qubits):
    q0, q1 = sys_qubits
    theta_init = 2 * np.arccos(1 / np.sqrt(3))
    qc.ry(theta_init, q0)
    qc.ch(q0, q1)

def close_three_paths(qc, sys_qubits):
    q0, q1 = sys_qubits
    theta_init = 2 * np.arccos(1 / np.sqrt(3))
    qc.ch(q0, q1)
    qc.ry(-theta_init, q0)

def weak_measure_paths(qc, sys_qubits, anc_qubits):
    q0, q1 = sys_qubits
    a1, a2, a3 = anc_qubits
    
    # Qiskit 1.0+ method for creating a doubly-controlled RY gate
    ccry = RYGate(THETA_W).control(2)
    
    # Measure Path 1 (|00>)
    qc.x(q0)
    qc.x(q1)
    qc.append(ccry, [q0, q1, a1])
    qc.x(q1)
    qc.x(q0)
    
    # Measure Path 2 (|10>)
    qc.x(q1)
    qc.append(ccry, [q0, q1, a2])
    qc.x(q1)
    
    # Measure Path 3 (|11>)
    qc.append(ccry, [q0, q1, a3])

### ============================================================
### CIRCUIT CONSTRUCTION
### ============================================================
circuits = []
keys = []

for phi in PHASES:
    # 5 Qubits: 2 for system, 3 for weak sensors
    qc = QuantumCircuit(5, 5, name=f"Surreal_phi_{phi:.3f}")
    
    # 1. Enter 3-path superposition
    init_three_paths(qc, [0, 1])
    qc.barrier()
    
    # 2. Weakly measure the paths
    weak_measure_paths(qc, [0, 1], [2, 3, 4])
    qc.barrier()
    
    # 3. Phase shift to sweep interference (Applied to Path 3: |11>)
    qc.cp(phi, 0, 1)
    qc.barrier()
    
    # 4. Close the interferometer
    close_three_paths(qc, [0, 1])
    qc.barrier()
    
    # 5. Final Measurement
    # Mapping: c0=q0, c1=q1 (System), c2=q2 (Sens1), c3=q3 (Sens2), c4=q4 (Sens3)
    qc.measure([0, 1, 2, 3, 4], [0, 1, 2, 3, 4])
    
    circuits.append(qc)
    keys.append(f"phi_{phi:.3f}")

### ============================================================
### TRANSPILATION & EXECUTION
### ============================================================
pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
opt_circuits = pm.run(circuits)

sampler = Sampler(mode=backend)
sampler.options.default_shots = NUM_SHOTS

print(f"\nSubmitting Surreal Trajectories sequence to {backend.name}...")
job = sampler.run(opt_circuits)
print(f"Job ID: {job.job_id()} - Awaiting execution...")

result = job.result()

### ============================================================
### DATA EXTRACTION & SURREAL TRAJECTORY ANALYSIS
### ============================================================
data = {}
print("\n--- SURREAL TRAJECTORIES RESULTS ---")
print("Evaluating weak values conditional on final strong measurement outcomes.\n")

for i, key in enumerate(keys):
    c = result[i].data.c.get_counts()
    data[key] = c
    
    # Qiskit string: "c4 c3 c2 c1 c0" -> "Sens3 Sens2 Sens1 Sys1 Sys0"
    # To isolate system outcomes (Interference pattern):
    sys_00 = sum(count for state, count in c.items() if state[3:5] == '00')
    sys_other = sum(count for state, count in c.items() if state[3:5] != '00')
    total = sys_00 + sys_other
    
    if total == 0: continue
    
    # Conditional Weak Sensor Excitations given the system closed the interferometer (|00>)
    sens1_given_00 = sum(count for state, count in c.items() if state[3:5] == '00' and state[2] == '1')
    sens2_given_00 = sum(count for state, count in c.items() if state[3:5] == '00' and state[1] == '1')
    sens3_given_00 = sum(count for state, count in c.items() if state[3:5] == '00' and state[0] == '1')
    
    p1 = sens1_given_00 / sys_00 if sys_00 > 0 else 0
    p2 = sens2_given_00 / sys_00 if sys_00 > 0 else 0
    p3 = sens3_given_00 / sys_00 if sys_00 > 0 else 0
    
    print(f"Phi {float(key.split('_')[1]):.3f} rad | System |00> Prob: {sys_00/total:.3f}")
    print(f"   Conditional Path Excitations -> Path 1: {p1:.4f} | Path 2: {p2:.4f} | Path 3: {p3:.4f}")

with open("surreal_trajectories_results.json", "w") as f:
    json.dump(data, f, indent=4)

### ============================================================
### THE THEORETICAL VERDICT
### ============================================================
print("\n=== THE SURREAL TRAJECTORY VERDICT ===")
print("Standard QM predicts specific symmetric correlations based on the phase.")
print("Bohmian mechanics predicts that non-crossing rules will force the trajectory")
print("to appear as if it traversed a path that the strong measurement contradicts.")
print("If Path 2 or Path 3 conditional excitations exhibit macroscopic oscillations that")
print("defy the direct geometric routing, a 'Surreal Trajectory' is verified, forcing a choice:")
print("Accept nonlocal pilot-wave guidance, or reject the ontology of the path entirely.")
