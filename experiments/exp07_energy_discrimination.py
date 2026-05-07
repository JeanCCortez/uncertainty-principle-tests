### ============================================================
### GHOST INTERFEROMETER: ENERGY DISCRIMINATION TEST
### Vacuum Filter via Cross-Resonance Hamiltonian (RZX)
### ============================================================

import json
import math
from qiskit import QuantumCircuit
from qiskit.circuit.library import RZXGate, RXGate
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

### ============================================================
### EXPERIMENT CONFIGURATION
### ============================================================
EXECUTION_MODE = "CLOUD"

MY_TOKEN = "KwgGZ3CMazqSPiRTF7gBgoENRS4SbCqcy7C_fIdbqd1-"
MY_CRN = "crn:v1:bluemix:public:quantum-computing:us-east:a/2751423f3df54bf9b963caabf1ceb7e4:e61c405d-5568-4f6b-97dd-0733e1af0fa3::" 

NUM_SHOTS = 4096
PHI_TARGET = 3.311

# Sweeping the physical coupling angle to find the discrimination threshold
DRIVE_ANGLES = [0.05, 0.10, 0.15, 0.20, 0.25]

if EXECUTION_MODE == "LOCAL":
    print("Initializing LOCAL simulator environment...")
    from qiskit_ibm_runtime.fake_provider import FakeLimaV2
    backend = FakeLimaV2()
else:
    print("Authenticating with IBM Quantum Platform...")
    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=MY_TOKEN, instance=MY_CRN)
    print("Scanning for the least busy operational quantum processor...")
    backend = service.least_busy(operational=True, simulator=False)

print(f"Target Backend: {backend.name} | Phase: {PHI_TARGET} rad")
print(f"Drive Angles (Theta): {DRIVE_ANGLES}")

### ============================================================
### CIRCUIT CONSTRUCTION: THE VACUUM FILTER
### Using RZX + RX to isolate the |1> energy state
### ============================================================
circuits = []
results_keys = []

for theta in DRIVE_ANGLES:
    qc = QuantumCircuit(4, 2, name=f"energy_drive_{theta:.2f}")
    
    qc.h(0)
    qc.barrier()
    
    # --- SENSOR A (Probes Reference Path) ---
    # RZX applies RX(theta) if control is |0>, and RX(-theta) if control is |1>.
    qc.append(RZXGate(theta), [0, 1])
    # RX(-theta) cancels the rotation for |0> (Empty Wave) and doubles it for |1> (Particle).
    qc.append(RXGate(-theta), [1])  
    
    qc.barrier()
    qc.p(PHI_TARGET, 0)
    qc.barrier()
    qc.x(0) # Invert control to probe Path B
    
    # --- SENSOR B (Probes Shadow Path) ---
    qc.append(RZXGate(theta), [0, 2])
    qc.append(RXGate(-theta), [2])  # Vacuum filter on Sensor B
    
    qc.x(0)
    qc.barrier()
    qc.h(0)
    
    # Measure logical sensors
    qc.measure([1, 2], [0, 1])
    
    circuits.append(qc)
    results_keys.append(f"theta_{theta:.2f}")

### ============================================================
### TRANSPILATION & EXECUTION
### ============================================================
pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
optimized_circuits = pm.run(circuits)

sampler = Sampler(mode=backend)
sampler.options.default_shots = NUM_SHOTS

print(f"\nSubmitting Vacuum-Filtered sequence to processor {backend.name}...")
job = sampler.run(optimized_circuits)
print(f"Job ID: {job.job_id()} - Awaiting physics execution...")

result = job.result()

### ============================================================
### DATA EXTRACTION & ANALYSIS
### ============================================================
data = {}
print("\n--- ENERGY DISCRIMINATION RESULTS ---")
print("If Asymmetry grows significantly with the drive angle -> Particle Energy Detected.")
print("If Asymmetry is zero/flat -> Empty wave holds equivalent physical weight.\n")

for i, theta in enumerate(DRIVE_ANGLES):
    c = result[i].data.c.get_counts()
    key = results_keys[i]
    data[key] = c
    
    # Qiskit maps measure([1, 2], [0, 1]) -> bit 1 is Sensor A (c0), bit 0 is Sensor B (c1)
    sens_a = sum(count for state, count in c.items() if state[1] == '1')
    sens_b = sum(count for state, count in c.items() if state[0] == '1')
    
    asym = sens_a - sens_b
    error = math.sqrt(sens_a + sens_b)
    
    print(f"Angle {theta:.2f} | Sens_A: {sens_a:4d} | Sens_B: {sens_b:4d} | Delta: {asym:+5d} ± {error:.0f}")

with open("energy_discrimination_results.json", "w") as f:
    json.dump(data, f, indent=4)

print("\nData exported to energy_discrimination_results.json.")