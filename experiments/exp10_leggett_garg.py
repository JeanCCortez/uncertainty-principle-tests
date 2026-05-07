### ============================================================
### GHOST INTERFEROMETER: TEST 10 - MACROSCOPIC REALISM
### Leggett-Garg Inequality (LGI) via Weak Measurements
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
THETA_W = 0.20  # Weak measurement coupling strength
NUM_PHASES = 15

# Sweeping the time evolution parameter (phi)
# Max violation theoretically expected at phi = pi/3 (~1.047 rad)
PHASES = np.linspace(0, np.pi, NUM_PHASES)

if EXECUTION_MODE == "LOCAL":
    print("Initializing LOCAL simulator environment...")
    from qiskit_ibm_runtime.fake_provider import FakeLimaV2
    backend = FakeLimaV2()
else:
    print("Authenticating with IBM Quantum Platform...")
    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=MY_TOKEN, instance=MY_CRN)
    print("Scanning for the least busy operational quantum processor...")
    backend = service.least_busy(operational=True, simulator=False)

print(f"Target Backend: {backend.name} | Weak Coupling: {THETA_W} rad")
print(f"Total Shots per Circuit: {NUM_SHOTS}")

### ============================================================
### SYMMETRIC WEAK MEASUREMENT MODULE
### Extracts partial Z-information from System (sys) into Ancilla (anc)
### without fundamentally collapsing the System's superposition.
### ============================================================
def apply_weak_measure(qc, sys, anc, bit):
    qc.barrier()
    qc.x(sys)
    qc.cry(THETA_W, sys, anc)
    qc.x(sys)
    qc.cry(-THETA_W, sys, anc)
    qc.h(anc) # Map phase to probability for X-basis measurement
    qc.measure(anc, bit)
    qc.barrier()

### ============================================================
### CIRCUIT CONSTRUCTION
### ============================================================
circuits = []
keys = []

for phi in PHASES:
    # --------------------------------------------------------------
    # C12: Measure at t1 (Weak), Evolve, Measure at t2 (Strong)
    # --------------------------------------------------------------
    qc_12 = QuantumCircuit(2, 2, name=f"C12_{phi:.3f}")
    qc_12.rx(np.pi/2, 0) # Initialize state to equator
    apply_weak_measure(qc_12, 0, 1, 0) # Weak measure at t1 -> Bit 0
    qc_12.rx(phi, 0) # Evolve to t2
    qc_12.measure(0, 1) # Strong measure at t2 -> Bit 1
    circuits.append(qc_12)
    
    # --------------------------------------------------------------
    # C23: Evolve, Measure at t2 (Weak), Evolve, Measure at t3 (Strong)
    # --------------------------------------------------------------
    qc_23 = QuantumCircuit(2, 2, name=f"C23_{phi:.3f}")
    qc_23.rx(np.pi/2, 0)
    qc_23.rx(phi, 0) # Evolve to t2
    apply_weak_measure(qc_23, 0, 1, 0) # Weak measure at t2 -> Bit 0
    qc_23.rx(phi, 0) # Evolve to t3
    qc_23.measure(0, 1) # Strong measure at t3 -> Bit 1
    circuits.append(qc_23)
    
    # --------------------------------------------------------------
    # C13: Measure at t1 (Weak), Evolve Double, Measure at t3 (Strong)
    # --------------------------------------------------------------
    qc_13 = QuantumCircuit(2, 2, name=f"C13_{phi:.3f}")
    qc_13.rx(np.pi/2, 0)
    apply_weak_measure(qc_13, 0, 1, 0) # Weak measure at t1 -> Bit 0
    qc_13.rx(2 * phi, 0) # Evolve to t3 directly
    qc_13.measure(0, 1) # Strong measure at t3 -> Bit 1
    circuits.append(qc_13)
    
    keys.append(f"{phi:.3f}")

### ============================================================
### TRANSPILATION & EXECUTION
### ============================================================
pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
opt_circuits = pm.run(circuits)

sampler = Sampler(mode=backend)
sampler.options.default_shots = NUM_SHOTS

print(f"\nSubmitting Leggett-Garg sequence to processor {backend.name}...")
job = sampler.run(opt_circuits)
print(f"Job ID: {job.job_id()} - Awaiting temporal correlation execution...")

result = job.result()

### ============================================================
### CORRELATION ANALYSIS
### ============================================================
data = {}
print("\n--- LEGGETT-GARG INEQUALITY RESULTS ---")
print("Classical Limit (Macroscopic Realism): K <= 1.0")
print("Quantum Limit: K <= 1.5\n")

def get_correlator(counts):
    c_raw = 0
    shots = sum(counts.values())
    for state, count in counts.items():
        # Qiskit output: "Bit1 Bit0" -> "Strong Weak"
        z_sys = 1 if state[0] == '0' else -1
        z_anc = 1 if state[1] == '0' else -1
        c_raw += (z_sys * z_anc) * count
    
    c_raw /= shots
    
    # Reconstruct true correlation by dividing out the weak coupling factor
    c_true = c_raw / math.sin(THETA_W)
    
    # Binomial error propagation through the coupling divisor
    err = 1.0 / (math.sqrt(shots) * math.sin(THETA_W))
    return c_true, err

max_K = -999
max_K_err = 0
max_phi = 0

for i, phi_str in enumerate(keys):
    idx = i * 3
    
    c12_counts = result[idx].data.c.get_counts()
    c23_counts = result[idx+1].data.c.get_counts()
    c13_counts = result[idx+2].data.c.get_counts()
    
    data[f"C12_phi_{phi_str}"] = c12_counts
    data[f"C23_phi_{phi_str}"] = c23_counts
    data[f"C13_phi_{phi_str}"] = c13_counts
    
    c12, err12 = get_correlator(c12_counts)
    c23, err23 = get_correlator(c23_counts)
    c13, err13 = get_correlator(c13_counts)
    
    # Leggett-Garg Parameter
    K = c12 + c23 - c13
    K_err = math.sqrt(err12**2 + err23**2 + err13**2)
    
    if K > max_K:
        max_K = K
        max_K_err = K_err
        max_phi = float(phi_str)
        
    print(f"Phi {float(phi_str):.2f} rad | C12: {c12:+.2f} | C23: {c23:+.2f} | C13: {c13:+.2f} || K = {K:+.3f} ± {K_err:.3f}")

with open("leggett_garg_results.json", "w") as f:
    json.dump(data, f, indent=4)

### ============================================================
### THE MACROSCOPIC REALISM VERDICT
### ============================================================
print("\n=== THE TEMPORAL REALISM VERDICT ===")
print(f"Maximum K observed: {max_K:.3f} ± {max_K_err:.3f} at Phi = {max_phi:.2f} rad")

significance = (max_K - 1.0) / max_K_err if max_K_err > 0 else 0

if max_K - max_K_err > 1.0:
    print(f"\n[!] MACROSCOPIC REALISM FALSIFIED: K > 1 established with {significance:.1f}σ significance.")
    print("The system does not possess a definite, objective state prior to observation.")
    print("Even using a non-invasive weak measurement, the trajectory through time is not classically defined.")
    print("Bohmian Theory is forced to admit that the pilot wave transmits temporal disturbances backwards/forwards non-locally.")
else:
    print("\n[-] REALISM MAINTAINED: K <= 1.0.")
    print("The correlations obey classical temporal logic. The particle behaves as if it has")
    print("a definite state at all times, surviving the non-invasive measurement without quantum temporal distortion.")