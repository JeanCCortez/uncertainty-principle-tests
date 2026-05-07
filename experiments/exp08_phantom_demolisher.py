### ============================================================
### GHOST INTERFEROMETER: THE PHANTOM DEMOLISHER
### Strong Decoupling Postulate Test
### ============================================================

import json
import math
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
DEMOLISH_PHASE = 2.0  # Strong destructive phase (~115 degrees)

if EXECUTION_MODE == "LOCAL":
    print("Initializing LOCAL simulator environment...")
    from qiskit_ibm_runtime.fake_provider import FakeLimaV2
    backend = FakeLimaV2()
else:
    print("Authenticating with IBM Quantum Platform...")
    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=MY_TOKEN, instance=MY_CRN)
    print("Scanning for the least busy operational quantum processor...")
    backend = service.least_busy(operational=True, simulator=False)

print(f"Target Backend: {backend.name} | Demolisher Phase: {DEMOLISH_PHASE} rad")
print(f"Total Shots per Circuit: {NUM_SHOTS}")

### ============================================================
### CIRCUIT CONSTRUCTION
### q0: Particle | q1: Temporal Anchor (Witness)
### ============================================================
circuits = []

# --- Circuit A: Absolute Control (Interferometer only) ---
qc_ctrl = QuantumCircuit(2, 2, name="A_Control")
qc_ctrl.h(0)
qc_ctrl.barrier()
qc_ctrl.h(0)
qc_ctrl.measure([0, 1], [0, 1])  # Measure to match output string size
circuits.append(qc_ctrl)

# --- Circuit B: The Demolisher ---
qc_dem = QuantumCircuit(2, 2, name="B_Demolisher")
qc_dem.h(0)
qc_dem.barrier()

# Temporal Anchor: Records if q0 is in |1> path
qc_dem.cx(0, 1) 
qc_dem.barrier()

# Demolisher: Applies destructive phase to q0 ONLY if q1 registered |1>
qc_dem.crz(DEMOLISH_PHASE, 1, 0)
qc_dem.barrier()

# Close Interferometer
qc_dem.h(0)

# Measure: c0 = q0 (Particle), c1 = q1 (Anchor)
# Qiskit outputs string as "c1 c0"
qc_dem.measure([0, 1], [0, 1])
circuits.append(qc_dem)

### ============================================================
### TRANSPILATION & EXECUTION
### ============================================================
pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
opt_circuits = pm.run(circuits)

sampler = Sampler(mode=backend)
sampler.options.default_shots = NUM_SHOTS

print(f"\nSubmitting Demolisher sequence to processor {backend.name}...")
job = sampler.run(opt_circuits)
print(f"Job ID: {job.job_id()} - Awaiting execution...")

result = job.result()

### ============================================================
### DATA EXTRACTION & POST-SELECTION ANALYSIS
### ============================================================
data = {}
print("\n--- DEMOLISHER RESULTS & POST-SELECTION ---")

# Qiskit Bitstring: "c1 c0" -> Index 0 is c1 (Anchor), Index 1 is c0 (Particle)
IDX_ANCHOR = 0
IDX_PARTICLE = 1

for i, name in enumerate(["A_Control", "B_Demolisher"]):
    c = result[i].data.c.get_counts()
    data[name] = c
    
    print(f"\n{name.upper()}:")
    
    for anchor_val in ['0', '1']:
        # Filter counts based on the anchor's state
        p0_counts = sum(count for state, count in c.items() if state[IDX_ANCHOR] == anchor_val and state[IDX_PARTICLE] == '0')
        p1_counts = sum(count for state, count in c.items() if state[IDX_ANCHOR] == anchor_val and state[IDX_PARTICLE] == '1')
        
        total = p0_counts + p1_counts
        pct_zero = (p0_counts / total * 100) if total > 0 else 0
        
        print(f"  Anchor (q1) = {anchor_val} | Particle |0>: {p0_counts:4d} | Particle |1>: {p1_counts:4d} | P(|0>): {pct_zero:.1f}%")

with open("phantom_demolisher_results.json", "w") as f:
    json.dump(data, f, indent=4)

### ============================================================
### EMPIRICAL VERDICT
### ============================================================
c_ctrl = result[0].data.c.get_counts()
c_dem = result[1].data.c.get_counts()

# Baseline Visibility (Circuit A)
ctrl_p0 = sum(count for state, count in c_ctrl.items() if state[IDX_PARTICLE] == '0')
ctrl_p1 = sum(count for state, count in c_ctrl.items() if state[IDX_PARTICLE] == '1')
vis_ctrl = abs(ctrl_p0 - ctrl_p1) / (ctrl_p0 + ctrl_p1) if (ctrl_p0 + ctrl_p1) > 0 else 0

# Demolisher Visibility (Post-selected on Anchor = |0>)
dem_q1_0 = {s: c for s, c in c_dem.items() if s[IDX_ANCHOR] == '0'}
dem_p0 = sum(c for s, c in dem_q1_0.items() if s[IDX_PARTICLE] == '0')
dem_p1 = sum(c for s, c in dem_q1_0.items() if s[IDX_PARTICLE] == '1')
total_q1_0 = dem_p0 + dem_p1
vis_dem_postsel = abs(dem_p0 - dem_p1) / total_q1_0 if total_q1_0 > 0 else 0

print(f"\n=== THE STRONG DECOUPLING VERDICT ===")
print(f"Baseline Visibility (Control): {vis_ctrl:.4f}")
print(f"Demolisher Visibility (Post-selected Anchor=|0>): {vis_dem_postsel:.4f}")
print(f"Total events analyzed in |0> post-selection: {total_q1_0}")

if vis_dem_postsel > 0.3 and total_q1_0 > (NUM_SHOTS * 0.1):
    print("\n[!] ABSOLUTE ANOMALY: Interference survived the conditional attack.")
    print("The particle was immune to operations on the empty path.")
    print("This falsifies Copenhagen entanglement predictions and isolates the particle trajectory.")
else:
    print("\n[-] COPENHAGEN CONFIRMED: The mere correlation with the Anchor destroyed the wave.")
    print("Even when the Demolisher was inactive (Anchor=|0>), the interference collapsed (V ~ 0).")
    print("The vacuum operation entangled the path, confirming orthodox non-local wave collapse.")