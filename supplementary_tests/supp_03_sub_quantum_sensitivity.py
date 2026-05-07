### ============================================================
### GHOST INTERFEROMETER: TEST 14 - SUB-QUANTUM SENSITIVITY
### Same Density Matrix via Distinct Physical Histories
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

# 1,000,000 total shots (500,000 per preparation method)
SHOTS_PER_CIRCUIT = 10000
NUM_CIRCUITS_PER_PREP = 50 

if EXECUTION_MODE == "LOCAL":
    from qiskit_ibm_runtime.fake_provider import FakeLimaV2
    backend = FakeLimaV2()
else:
    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=MY_TOKEN, instance=MY_CRN)
    backend = service.least_busy(operational=True, simulator=False)

### ============================================================
### CIRCUIT CONSTRUCTION
### Preparation A: Single Macroscopic Pulse (RY pi/2)
### Preparation B: Two Microscopic Pulses (RY pi/4 + RY pi/4)
### Both prepare the exact same mathematical state: |+>
### ============================================================
circuits = []
keys = []

# Protocol A: Direct 90-degree rotation
qc_A = QuantumCircuit(1, 1, name="Prep_A_Single")
qc_A.ry(np.pi / 2, 0)
qc_A.measure(0, 0)

for _ in range(NUM_CIRCUITS_PER_PREP):
    circuits.append(qc_A)
    keys.append("A")

# Protocol B: Fragmented 90-degree rotation
# barrier() enforces the transpiler/hardware to execute two distinct microwave pulses
qc_B = QuantumCircuit(1, 1, name="Prep_B_Split")
qc_B.ry(np.pi / 4, 0)
qc_B.barrier()
qc_B.ry(np.pi / 4, 0)
qc_B.measure(0, 0)

for _ in range(NUM_CIRCUITS_PER_PREP):
    circuits.append(qc_B)
    keys.append("B")

### ============================================================
### TRANSPILATION & EXECUTION
### optimization_level=1 ensures the barrier is respected and 
### the two pulses in Protocol B are not merged mathematically.
### ============================================================
pm = generate_preset_pass_manager(optimization_level=1, backend=backend)
opt_circuits = pm.run(circuits)

sampler = Sampler(mode=backend)
sampler.options.default_shots = SHOTS_PER_CIRCUIT

job = sampler.run(opt_circuits)
result = job.result()

### ============================================================
### DATA EXTRACTION & SUB-QUANTUM SENSITIVITY ANALYSIS
### ============================================================
data = {"A": [], "B": []}

count_1_A = 0
count_1_B = 0

for i, key in enumerate(keys):
    c = result[i].data.c.get_counts()
    data[key].append(c)
    
    if key == "A":
        count_1_A += c.get("1", 0)
    else:
        count_1_B += c.get("1", 0)

total_A = SHOTS_PER_CIRCUIT * NUM_CIRCUITS_PER_PREP
total_B = SHOTS_PER_CIRCUIT * NUM_CIRCUITS_PER_PREP

p_A = count_1_A / total_A
p_B = count_1_B / total_B

# Z-Test for two proportions
# Pooled probability
p_pool = (count_1_A + count_1_B) / (total_A + total_B)
standard_error = math.sqrt(p_pool * (1 - p_pool) * ((1 / total_A) + (1 / total_B)))

z_score = (p_A - p_B) / standard_error if standard_error > 0 else 0

with open("sub_quantum_sensitivity_results.json", "w") as f:
    json.dump({
        "Protocol_A": {"shots": total_A, "ones": count_1_A, "p": p_A},
        "Protocol_B": {"shots": total_B, "ones": count_1_B, "p": p_B},
        "Z_Score": z_score
    }, f, indent=4)

### ============================================================
### THEORETICAL VERDICT
### ============================================================
print(f"\n=== SUB-QUANTUM INITIAL CONDITIONS VERDICT ===")
print(f"Protocol A (1x 90° Pulse) P(|1>): {p_A:.6f}")
print(f"Protocol B (2x 45° Pulse) P(|1>): {p_B:.6f}")
print(f"Difference (Delta): {(p_A - p_B):+.6f}")
print(f"Statistical Significance (Z-Score): {z_score:+.2f}σ")

if abs(z_score) > 5.0:
    print("\n[!] ANOMALY DETECTED: The two mathematically identical states yielded different physical statistics.")
    print("The system is sensitive to the physical history of its preparation (the sequence of microwave pulses).")
    print("This implies the existence of sub-quantum hidden variables coupling to the gate execution.")
elif abs(z_score) > 3.0:
    print("\n[?] STRONG INDICATION: Potential sensitivity to initial conditions (>3σ).")
    print("Hardware calibration drift could be responsible, but the deviation warrants deeper investigation.")
else:
    print("\n[-] COPENHAGEN CONFIRMED: No sensitivity to physical history detected.")
    print("The two distinct preparations produced statistically indistinguishable random distributions.")
    print("The quantum state vector completely and exhaustively describes the system.")