### ============================================================
### GHOST INTERFEROMETER: TEMPORAL DURATION SWEEP
### Zero Noise Extrapolation (ZNE) for T1-induced Asymmetry
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

NUM_SHOTS = 4096
THETA = 0.10
PHI_TARGET = 3.311

# Controlled delays in nanoseconds (forced at hardware level)
DELAY_NS = [0, 50, 100, 200]

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
print(f"Theta: {THETA} rad | Phase: {PHI_TARGET} rad")
print(f"Delay steps: {DELAY_NS} ns")
print(f"Shots per circuit: {NUM_SHOTS}")
print(f"Total iterations: {NUM_SHOTS * len(DELAY_NS) * 2}")

### ============================================================
### LOGICAL MAPPING & DELAY INSTRUCTION
### ============================================================
# measure([1, 2], [0, 1]) -> c0=q1, c1=q2
# String format is "c1 c0". Index 1 is q1 (Sensor A). Index 0 is q2 (Sensor B).
mapping = {
    "std_fwd": {"A": 1, "B": 0},
    "std_rev": {"A": 1, "B": 0}
}

def add_delay(qc, delay_in_ns):
    """Enforces strict hardware-level temporal delay on the particle qubit."""
    if delay_in_ns == 0:
        return
    qc.barrier()
    qc.delay(delay_in_ns, 0, unit='ns')
    qc.barrier()

### ============================================================
### CIRCUIT CONSTRUCTION
### ============================================================
circuits = []

# 1. STD-FORWARD: Sensor A (q1) -> Phase -> [Delay] -> Sensor B (q2)
for delay in DELAY_NS:
    name = f"std_fwd_T{delay}"
    qc = QuantumCircuit(4, 2, name=name)
    qc.h(0)
    qc.barrier()
    qc.cry(THETA, 0, 1)      # Sensor A (Time 1)
    qc.barrier()
    qc.p(PHI_TARGET, 0)      
    qc.barrier()
    add_delay(qc, delay)     # Variable delay injection
    qc.x(0)
    qc.cry(THETA, 0, 2)      # Sensor B (Time 2)
    qc.x(0)
    qc.barrier()
    qc.h(0)
    qc.measure([1, 2], [0, 1])
    circuits.append(qc)

# 2. STD-REVERSE: Sensor B (q2) -> Phase -> [Delay] -> Sensor A (q1)
for delay in DELAY_NS:
    name = f"std_rev_T{delay}"
    qc = QuantumCircuit(4, 2, name=name)
    qc.h(0)
    qc.barrier()
    qc.x(0)
    qc.cry(THETA, 0, 2)      # Sensor B (Time 1)
    qc.x(0)
    qc.barrier()
    qc.p(PHI_TARGET, 0)      
    qc.barrier()
    add_delay(qc, delay)     # Variable delay injection
    qc.cry(THETA, 0, 1)      # Sensor A (Time 2)
    qc.barrier()
    qc.h(0)
    qc.measure([1, 2], [0, 1])
    circuits.append(qc)

### ============================================================
### TRANSPILATION AND EXECUTION
### ============================================================
pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
optimized_circuits = pm.run(circuits)

sampler = Sampler(mode=backend)
sampler.options.default_shots = NUM_SHOTS

print(f"\nSubmitting execution sequence to processor {backend.name}...")
job = sampler.run(optimized_circuits)
print(f"Job ID: {job.job_id()} - Awaiting execution...")

result = job.result()

### ============================================================
### DATA EXTRACTION & POISSONIAN ERROR PROPAGATION
### ============================================================
data = {}
results_by_delay = {}

print("\n--- RAW ASYMMETRY MEASUREMENTS ---")

for i, qc in enumerate(circuits):
    name = qc.name
    c = result[i].data.c.get_counts()
    data[name] = c

    # Parse logical mapping
    direction = "std_fwd" if "fwd" in name else "std_rev"
    idx_A = mapping[direction]["A"]
    idx_B = mapping[direction]["B"]

    sens_a = sum(count for state, count in c.items() if state[idx_A] == '1')
    sens_b = sum(count for state, count in c.items() if state[idx_B] == '1')

    asym = sens_a - sens_b
    error = math.sqrt(sens_a + sens_b)

    delay_val = int(name.split("_T")[1])
    direction_key = "fwd" if "fwd" in name else "rev"

    if delay_val not in results_by_delay:
        results_by_delay[delay_val] = {}
    
    results_by_delay[delay_val][direction_key] = {'asym': asym, 'error': error}

    print(f"{name.ljust(15)} | Sens_A: {sens_a:4d} | Sens_B: {sens_b:4d} | Delta: {asym:+6.1f} ± {error:.1f}")

with open("duration_sweep_results.json", "w") as f:
    json.dump(data, f, indent=4)

### ============================================================
### ZERO NOISE EXTRAPOLATION (ZNE) ANALYSIS
### ============================================================
print("\n--- TEMPORAL EXTRAPOLATION ANALYSIS ---")

phys_asym = []
phys_err = []
delays_sorted = sorted(results_by_delay.keys())

for d in delays_sorted:
    asym_fwd = results_by_delay[d]["fwd"]["asym"]
    asym_rev = results_by_delay[d]["rev"]["asym"]
    err_fwd = results_by_delay[d]["fwd"]["error"]
    err_rev = results_by_delay[d]["rev"]["error"]

    # Isolate physical signal by averaging standard and reverse (canceling sequence bias)
    delta_phys = (asym_fwd + asym_rev) / 2
    err_phys = math.sqrt(err_fwd**2 + err_rev**2) / 2

    phys_asym.append(delta_phys)
    phys_err.append(err_phys)

    print(f"Delay +{d:3d} ns | Δ_phys: {delta_phys:+7.2f} ± {err_phys:.2f} counts")

# Weighted linear fit: y = intercept + slope * x
x = np.array(delays_sorted, dtype=float)
y = np.array(phys_asym, dtype=float)
w = 1.0 / np.array(phys_err, dtype=float)**2

W = np.diag(w)
X = np.vstack([np.ones_like(x), x]).T
XTW = X.T @ W
XTWX = XTW @ X
XTWy = XTW @ y

beta = np.linalg.solve(XTWX, XTWy)
intercept = beta[0]
slope = beta[1]

cov = np.linalg.inv(XTWX)
intercept_err = math.sqrt(cov[0, 0])
slope_err = math.sqrt(cov[1, 1])

sigma_intercept = intercept / intercept_err if intercept_err > 0 else 0

### ============================================================
### FINAL VERDICT
### ============================================================
print("\n=== ZNE EXTRAPOLATION VERDICT (T=0) ===")
print(f"Extrapolated Physical Asymmetry (T=0): {intercept:+.2f} ± {intercept_err:.2f} counts")
print(f"T1 Decoherence Rate (Slope):           {slope:+.4f} ± {slope_err:.4f} counts/ns")
print(f"Statistical Significance at T=0:         {sigma_intercept:.2f}σ")

print("\n--- SCIENTIFIC CONCLUSION ---")
if abs(sigma_intercept) < 2.0:
    print("Null Result. The extrapolated asymmetry at zero duration is consistent with zero.")
    print("All residual asymmetry is strictly a function of T1 relaxation time.")
    print("The theoretical symmetry of the probability wave remains unbroken.")
elif 2.0 <= abs(sigma_intercept) < 3.0:
    print("Marginal evidence of residual asymmetry at zero duration. T1 decoherence")
    print("cannot fully account for the signal, but confidence is insufficient for discovery.")
else:
    print("Significant Discovery. Asymmetry persists at zero duration (>3σ).")
    print("The signal demonstrates a robust ontological divergence between paths")
    print("that is independent of both hardware spatial mapping and T1 temporal decoherence.")