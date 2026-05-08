### ============================================================
### GHOST INTERFEROMETER: TEST 13 - QUANTUM CONTEXTUALITY
### Klyachko-Can-Binicioğlu-Shumovsky (KCBS) Inequality
### ============================================================

import json
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import UnitaryGate
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

### ============================================================
### CONFIGURATION
### ============================================================
EXECUTION_MODE = "CLOUD"
MY_TOKEN = "YOUR_TOKEN_HERE"
MY_CRN = "YOUR_CRN_HERE" # Get this from the 'Instances' tab on quantum.cloud.ibm.com
NUM_SHOTS = 8192

if EXECUTION_MODE == "LOCAL":
    from qiskit_ibm_runtime.fake_provider import FakeLimaV2
    backend = FakeLimaV2()
else:
    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=MY_TOKEN, instance=MY_CRN)
    backend = service.least_busy(operational=True, simulator=False)

print(f"Target Backend: {backend.name}")
print(f"Total Shots per Context: {NUM_SHOTS}")

### ============================================================
### KCBS PENTAGRAM & QUTRIT EMBEDDING
### Embedding a 3-level system in 2 qubits:
### |0>_3 = |00>, |1>_3 = |01>, |2>_3 = |10>
### The optimal KCBS state is the pole vector (0, 0, 1)^T -> |10>
### ============================================================
# Exact math for orthogonal KCBS rays
c_pi5 = np.cos(np.pi / 5)
cos_theta = np.sqrt(c_pi5 / (1 + c_pi5))
sin_theta = np.sqrt(1 / (1 + c_pi5))

# Generate the 5 perfectly orthogonal adjacent vectors
v = []
for k in range(5):
    vec = np.array([
        sin_theta * np.cos(4 * np.pi * k / 5),
        sin_theta * np.sin(4 * np.pi * k / 5),
        cos_theta
    ])
    v.append(vec)

circuits = []
keys = []

for i in range(5):
    # Adjacent compatible observables A_i and A_{i+1}
    v1 = v[i]
    v2 = v[(i + 1) % 5]
    
    # Third orthogonal basis vector to complete 3D space
    v3 = np.cross(v1, v2)
    v3 = v3 / np.linalg.norm(v3)
    
    # Matrix whose rows are the eigenvectors
    U_3x3 = np.vstack([v1, v2, v3])
    
    # SVD projection to mathematically enforce strict unitarity against floating point noise
    u_svd, _, vh_svd = np.linalg.svd(U_3x3)
    U_3x3_strict = u_svd @ vh_svd
    
    # Pad to 4x4 for 2-qubit system (identity on |11> state)
    U_4x4 = np.eye(4, dtype=complex)
    U_4x4[0:3, 0:3] = U_3x3_strict
    
    # Measurement gate rotates the measurement basis into the computational Z-basis
    meas_gate = UnitaryGate(U_4x4, label=f"KCBS_{i}_{i+1}")
    
    qc = QuantumCircuit(2, 2, name=f"Context_{i}_{i+1}")
    
    # Prepare optimal state |10> corresponding to the pole (0, 0, 1)^T
    qc.x(1) 
    qc.barrier()
    
    # Apply measurement basis rotation
    qc.append(meas_gate, [0, 1])
    qc.barrier()
    
    qc.measure([0, 1], [0, 1])
    
    circuits.append(qc)
    keys.append(f"C_{i}_{(i+1)%5}")

### ============================================================
### TRANSPILATION & EXECUTION
### ============================================================
pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
opt_circuits = pm.run(circuits)

sampler = Sampler(mode=backend)
sampler.options.default_shots = NUM_SHOTS

print("Submitting Contextuality sequence...")
job = sampler.run(opt_circuits)
print(f"Job ID: {job.job_id()} - Awaiting execution...")

result = job.result()

### ============================================================
### DATA EXTRACTION & CONTEXTUALITY ANALYSIS
### ============================================================
data = {}
kcbs_sum = 0
err_sum_sq = 0

print("\n--- KCBS CONTEXTUALITY RESULTS ---")
print("Non-Contextual Hidden Variable Limit: sum <A_i A_{i+1}> >= -3")
print("Quantum Mechanical Limit:             sum <A_i A_{i+1}> >= -3.944\n")

for i, key in enumerate(keys):
    c = result[i].data.c.get_counts()
    data[key] = c
    
    # State mapping in measurement basis:
    # '00' -> System was in v1 -> A_i = +1, A_{i+1} = -1 -> Product = -1
    # '01' -> System was in v2 -> A_i = -1, A_{i+1} = +1 -> Product = -1
    # '10' -> System was in v3 -> A_i = -1, A_{i+1} = -1 -> Product = +1
    # '11' -> Leakage
    
    count_00 = c.get("00", 0)
    count_01 = c.get("01", 0)
    count_10 = c.get("10", 0)
    count_11 = c.get("11", 0)
    
    total = count_00 + count_01 + count_10
    if total == 0: continue
    
    # Expectation value of A_i * A_{i+1}
    correlator = (count_10 - count_00 - count_01) / total
    
    # Statistical error (binomial)
    variance = 1 - correlator**2
    err = np.sqrt(variance / total) if total > 0 else 0
    
    kcbs_sum += correlator
    err_sum_sq += err**2
    
    print(f"Context {key}: <A_i A_i+1> = {correlator:+.4f} ± {err:.4f} (Leakage to |11>: {count_11})")

kcbs_err = np.sqrt(err_sum_sq)

with open("kcbs_contextuality_results.json", "w") as f:
    json.dump(data, f, indent=4)

### ============================================================
### THE CONTEXTUALITY VERDICT
### ============================================================
print(f"\n=== THE KCHBS INEQUALITY VERDICT ===")
print(f"KCBS Sum: {kcbs_sum:+.4f} ± {kcbs_err:.4f}")

significance = (-3.0 - kcbs_sum) / kcbs_err if kcbs_err > 0 else 0

if kcbs_sum + kcbs_err < -3.0:
    print(f"\n[!] CONTEXTUALITY PROVEN: Inequality violated with {significance:.1f}σ significance.")
    print("The values of the observables CANNOT be pre-assigned independently of the measurement context.")
    print("This falsifies Non-Contextual Hidden Variables. Any viable Realism (like Bohm) MUST be context-dependent.")
else:
    print("\n[-] INEQUALITY MAINTAINED: KCBS Sum >= -3.")
    print("The system behaves consistently with pre-existing, non-contextual realistic values.")
