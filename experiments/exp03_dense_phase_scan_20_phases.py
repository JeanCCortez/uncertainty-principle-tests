### ============================================================
### GHOST INTERFEROMETER: DENSE PHASE SCAN (20 PHASES)
### Testing the Asymmetry of the Quantum Vacuum
### ============================================================

import json
import math
import numpy as np
from qiskit import QuantumCircuit
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

### ============================================================
### EXECUTION MODE CONTROLLER
### ============================================================
EXECUTION_MODE = "CLOUD"  # Keep as "CLOUD" to run on IBM Quantum hardware

### ============================================================
### BACKEND CONFIGURATION
### ============================================================
MY_TOKEN = "YOUR_TOKEN_HERE"
MY_CRN = "YOUR_CRN_HERE" 

NUM_SHOTS = 8192
THETA = 0.2  # Weak measurement angle
NUM_PHASES = 20

if EXECUTION_MODE == "LOCAL":
    print("Initializing LOCAL simulator...")
    from qiskit_ibm_runtime.fake_provider import FakeLimaV2
    backend = FakeLimaV2()
else:
    print("Authenticating with IBM Cloud (Real Hardware)...")
    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=MY_TOKEN, instance=MY_CRN)
    print("Scanning IBM Cloud for the least busy operational quantum processor...")
    backend = service.least_busy(operational=True, simulator=False)

print(f"Backend: {backend.name} | Shots/phase: {NUM_SHOTS} | Phases: {NUM_PHASES} | Total shots: {NUM_SHOTS * NUM_PHASES}")

### ============================================================
### BUILDING THE 20 CIRCUITS
### q0: Particle | q1: Sensor A | q2: Sensor B | q3: Isolation
### ============================================================
phases = np.linspace(0, 2 * np.pi, NUM_PHASES)
circuits = []

for i, phi in enumerate(phases):
    # 4 qubits, 2 classical bits (we only measure the sensors)
    qc = QuantumCircuit(4, 2)
    qc.name = f"phi_{i}"
    
    # 1. Superposition
    qc.h(0)
    
    # 2. Sensor A probes Path A (Particle path, q0 = |1>)
    qc.cry(THETA, 0, 1)
    
    # 3. Phase shift on Path A
    qc.p(phi, 0)
    
    # 4. Sensor B probes Path B (Shadow path, q0 = |0>)
    # CRITICAL PHYSICS FIX: Invert q0 to map |0> to |1> for the CRY gate
    qc.x(0)
    qc.cry(THETA, 0, 2)
    qc.x(0)
    
    # 5. Close interferometer
    qc.h(0)
    
    # 6. Measure ONLY Sensor A (q1) and Sensor B (q2)
    # q1 -> classical bit 0 | q2 -> classical bit 1
    qc.measure([1, 2], [0, 1])
    
    circuits.append(qc)

### ============================================================
### TRANSPILATION AND EXECUTION
### ============================================================
pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
optimized_circuits = pm.run(circuits)

sampler = Sampler(mode=backend)
sampler.options.default_shots = NUM_SHOTS 

print(f"Sending batch job to processor {backend.name}...")
job = sampler.run(optimized_circuits)
print(f"Job ID: {job.job_id()}. Waiting for global queue... Do not close the terminal.")

result = job.result()

### ============================================================
### RAW DATA COLLECTION AND JSON EXPORT
### ============================================================
data = {}
for i in range(NUM_PHASES):
    pub_result = result[i]
    # Correct V2 access to classical register 'c'
    counts = pub_result.data.c.get_counts()
    
    key = f"phi_{phases[i]:.3f}"
    data[key] = counts
    print(f"\n--- {key} ---")
    print(f"Counts: {counts}")

with open("dense_scan_results.json", "w") as f:
    json.dump(data, f, indent=4)

print("\n============================================================")
print("EXECUTION COMPLETE. Data saved to dense_scan_results.json")
print("============================================================")

### ============================================================
### REAL-TIME ASYMMETRY ANALYSIS
### ============================================================
print("\n--- PRELIMINARY ASYMMETRY ANALYSIS ---")

asymmetries = []
for i in range(NUM_PHASES):
    key = f"phi_{phases[i]:.3f}"
    c = data[key]
    
    # Qiskit strings are "c1 c0". 
    # c0 (index 1 in string) is q1 (Sensor A). c1 (index 0 in string) is q2 (Sensor B).
    q1_count = sum(count for state, count in c.items() if state[1] == '1')
    q2_count = sum(count for state, count in c.items() if state[0] == '1')
    
    asym = q1_count - q2_count
    asymmetries.append(asym)
    
    error = np.sqrt(q1_count + q2_count) # Poissonian statistical error
    print(f"Phase {phases[i]:.2f} rad | Sensor A={q1_count}, Sensor B={q2_count} | Asymmetry={asym:+.0f} ± {error:.0f}")

mean_asym = np.mean(asymmetries)
std_error = np.std(asymmetries) / np.sqrt(NUM_PHASES)
sigma = mean_asym / std_error if std_error > 0 else 0

print(f"\n=== FINAL STATISTICAL VERDICT ===")
print(f"Mean Asymmetry: {mean_asym:.1f} ± {std_error:.1f} counts")
print(f"Statistical Significance: {sigma:.2f}σ")

if abs(sigma) > 5.0:
    print("EXTRAORDINARY RESULT! Asymmetry detected with >5σ. The vacuum is not isotropic.")
elif abs(sigma) > 3.0:
    print("STRONG EVIDENCE of asymmetry (>3σ). Requires independent replication.")
else:
    print("NULL RESULT. Asymmetry within noise margins. Data establishes upper limits.")