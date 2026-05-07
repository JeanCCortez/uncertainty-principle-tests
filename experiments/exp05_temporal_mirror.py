### ============================================================
### GHOST INTERFEROMETER: ABSOLUTE CONTROL QUADRANT
### Elimination of Spatial and Temporal (T1) Systematics
### ============================================================

import json
import math
import numpy as np
from qiskit import QuantumCircuit
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

### ============================================================
### BACKEND AND EXPERIMENT CONFIGURATION
### ============================================================
EXECUTION_MODE = "CLOUD"

MY_TOKEN = "KwgGZ3CMazqSPiRTF7gBgoENRS4SbCqcy7C_fIdbqd1-"
MY_CRN = "crn:v1:bluemix:public:quantum-computing:us-east:a/2751423f3df54bf9b963caabf1ceb7e4:e61c405d-5568-4f6b-97dd-0733e1af0fa3::" 

NUM_SHOTS = 8192
THETA = 0.10
PHI_TARGET = 3.311  # Empirically determined peak phase

if EXECUTION_MODE == "LOCAL":
    print("Initializing LOCAL simulator environment...")
    from qiskit_ibm_runtime.fake_provider import FakeLimaV2
    backend = FakeLimaV2()
else:
    print("Authenticating with IBM Quantum Platform...")
    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=MY_TOKEN, instance=MY_CRN)
    print("Scanning for the least busy operational quantum processor...")
    backend = service.least_busy(operational=True, simulator=False)

print(f"Target Backend: {backend.name} | Theta: {THETA} rad | Phase: {PHI_TARGET} rad")
print(f"Total iterations: {NUM_SHOTS * 4} (4 control quadrants)")

### ============================================================
### LOGICAL-TO-PHYSICAL MAPPING DICTIONARY
### Qiskit string format is "c1 c0".
### All circuits use: measure([1, 2], [0, 1]) -> c0=q1, c1=q2.
### String index 0 is c1 (q2). String index 1 is c0 (q1).
###
### Sensor A (Reference): Unwrapped CRY gate (probes |1>).
### Sensor B (Shadow): X-wrapped CRY gate (probes |0>).
### ============================================================
mapping = {
    # Std: Sensor A is on q1 (index 1), Sensor B is on q2 (index 0)
    "std_fwd":  {"A": 1, "B": 0},
    "std_rev":  {"A": 1, "B": 0},
    # Swap: Sensor A is on q2 (index 0), Sensor B is on q1 (index 1)
    "swap_fwd": {"A": 0, "B": 1},
    "swap_rev": {"A": 0, "B": 1}
}

### ============================================================
### CIRCUIT CONSTRUCTION
### ============================================================
circuits = []

# --------------------------------------------------------------
# 1. STD-FORWARD: Sensor A (q1) precedes Sensor B (q2)
# --------------------------------------------------------------
qc_std_fwd = QuantumCircuit(4, 2, name="std_fwd")
qc_std_fwd.h(0)
qc_std_fwd.barrier()
qc_std_fwd.cry(THETA, 0, 1)      # Sensor A (Time 1)
qc_std_fwd.barrier()
qc_std_fwd.p(PHI_TARGET, 0)      
qc_std_fwd.barrier()
qc_std_fwd.x(0)
qc_std_fwd.cry(THETA, 0, 2)      # Sensor B (Time 2)
qc_std_fwd.x(0)
qc_std_fwd.barrier()
qc_std_fwd.h(0)
qc_std_fwd.measure([1, 2], [0, 1])
circuits.append(qc_std_fwd)

# --------------------------------------------------------------
# 2. STD-REVERSE: Sensor B (q2) precedes Sensor A (q1)
# --------------------------------------------------------------
qc_std_rev = QuantumCircuit(4, 2, name="std_rev")
qc_std_rev.h(0)
qc_std_rev.barrier()
qc_std_rev.x(0)
qc_std_rev.cry(THETA, 0, 2)      # Sensor B (Time 1)
qc_std_rev.x(0)
qc_std_rev.barrier()
qc_std_rev.p(PHI_TARGET, 0)      
qc_std_rev.barrier()
qc_std_rev.cry(THETA, 0, 1)      # Sensor A (Time 2)
qc_std_rev.barrier()
qc_std_rev.h(0)
qc_std_rev.measure([1, 2], [0, 1])
circuits.append(qc_std_rev)

# --------------------------------------------------------------
# 3. SWAP-FORWARD: Sensor A (q2) precedes Sensor B (q1)
# --------------------------------------------------------------
qc_swap_fwd = QuantumCircuit(4, 2, name="swap_fwd")
qc_swap_fwd.h(0)
qc_swap_fwd.barrier()
qc_swap_fwd.cry(THETA, 0, 2)     # Sensor A (Time 1)
qc_swap_fwd.barrier()
qc_swap_fwd.p(PHI_TARGET, 0)
qc_swap_fwd.barrier()
qc_swap_fwd.x(0)
qc_swap_fwd.cry(THETA, 0, 1)     # Sensor B (Time 2)
qc_swap_fwd.x(0)
qc_swap_fwd.barrier()
qc_swap_fwd.h(0)
qc_swap_fwd.measure([1, 2], [0, 1])
circuits.append(qc_swap_fwd)

# --------------------------------------------------------------
# 4. SWAP-REVERSE: Sensor B (q1) precedes Sensor A (q2)
# --------------------------------------------------------------
qc_swap_rev = QuantumCircuit(4, 2, name="swap_rev")
qc_swap_rev.h(0)
qc_swap_rev.barrier()
qc_swap_rev.x(0)
qc_swap_rev.cry(THETA, 0, 1)     # Sensor B (Time 1)
qc_swap_rev.x(0)
qc_swap_rev.barrier()
qc_swap_rev.p(PHI_TARGET, 0)
qc_swap_rev.barrier()
qc_swap_rev.cry(THETA, 0, 2)     # Sensor A (Time 2)
qc_swap_rev.barrier()
qc_swap_rev.h(0)
qc_swap_rev.measure([1, 2], [0, 1])
circuits.append(qc_swap_rev)

### ============================================================
### TRANSPILATION AND EXECUTION
### ============================================================
pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
optimized_circuits = pm.run(circuits)

sampler = Sampler(mode=backend)
sampler.options.default_shots = NUM_SHOTS 

print(f"Submitting job to processor {backend.name}...")
job = sampler.run(optimized_circuits)
print(f"Job ID: {job.job_id()} - Awaiting execution...")

result = job.result()

### ============================================================
### DATA EXTRACTION AND POISSONIAN ERROR PROPAGATION
### ============================================================
data = {}
metrics = {}
circuit_names = ["std_fwd", "std_rev", "swap_fwd", "swap_rev"]

print("\n--- RAW ASYMMETRY DATA ---")

for i, name in enumerate(circuit_names):
    c = result[i].data.c.get_counts()
    data[name] = c
    
    idx_A = mapping[name]["A"]
    idx_B = mapping[name]["B"]
    
    sens_a = sum(count for state, count in c.items() if state[idx_A] == '1')
    sens_b = sum(count for state, count in c.items() if state[idx_B] == '1')
    
    asym = sens_a - sens_b
    error = math.sqrt(sens_a + sens_b) 
    
    metrics[name] = {'asym': asym, 'error': error}
    print(f"{name.ljust(10)} | Sens_A: {sens_a} | Sens_B: {sens_b} | Delta: {asym:+.1f} ± {error:.1f}")

with open("control_quadrant_results.json", "w") as f:
    json.dump(data, f, indent=4)

### ============================================================
### STATISTICAL SIGNIFICANCE EVALUATION
### ============================================================
# Averaging Forward and Reverse to isolate physical signal from T1 decay
delta_phys_std = (metrics["std_fwd"]["asym"] + metrics["std_rev"]["asym"]) / 2
delta_phys_swap = (metrics["swap_fwd"]["asym"] + metrics["swap_rev"]["asym"]) / 2

# Averaging Standard and Swapped maps to isolate physical signal from hardware bias
true_physics_signal = (delta_phys_std + delta_phys_swap) / 2

# Exact propagation of independent Poisson errors
variance_sum = sum(metrics[name]["error"]**2 for name in circuit_names)
true_physics_err = math.sqrt(variance_sum) / 4

sigma = true_physics_signal / true_physics_err if true_physics_err > 0 else 0

print("\n--- STATISTICAL VERDICT ---")
print(f"Extracted Physical Signal: {true_physics_signal:+.2f} ± {true_physics_err:.2f} counts")
print(f"Statistical Significance: {sigma:.2f}σ")

print("\n--- EMPIRICAL CONCLUSION ---")
if abs(sigma) < 2.0:
    print("Null Result. The preliminary asymmetry is fully accounted for by T1 decoherence")
    print("and gate execution order. Path symmetry is maintained within experimental margins.")
elif 2.0 <= abs(sigma) < 3.0:
    print("Marginal evidence of persistent asymmetry. The physical signal survives temporal")
    print("and spatial controls but falls below the 3-sigma threshold for definitive claims.")
else:
    print("Robust confirmation. The path asymmetry survives both temporal inversion and")
    print("hardware mapping controls with statistical significance (>3σ).")
    print("Data indicates a physical divergence from symmetric path probabilities.")