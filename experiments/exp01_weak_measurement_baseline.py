### ============================================================
### EXPERIMENT: SPATIAL PERTURBATION AND UNCERTAINTY TEST
### Execution Plan on the IBM Quantum Platform
### ============================================================

import json
from qiskit import QuantumCircuit
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

### ============================================================
### EXECUTION MODE CONTROLLER
### ============================================================
# Switch to "CLOUD" when you are ready to fire at the physical quantum chip
EXECUTION_MODE = "CLOUD"  

### ============================================================
### BACKEND CONFIGURATION
### ============================================================
# Credentials for IBM Cloud
MY_TOKEN = "YOUR_TOKEN_HERE"
MY_CRN = "YOUR_CRN_HERE" # Get this from the 'Instances' tab on quantum.cloud.ibm.com

NUM_SHOTS = 8192
THETA = 0.2  # Weak measurement angle (interaction with spatial perturbation)

# Service authentication and Auto-Backend retrieval
if EXECUTION_MODE == "LOCAL":
    print("Initializing LOCAL simulator (Fake 5-Qubit Chip bypassing limit)...")
    from qiskit_ibm_runtime.fake_provider import FakeLimaV2
    backend = FakeLimaV2()
else:
    print("Authenticating with IBM Cloud (Real Hardware)...")
    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=MY_TOKEN, instance=MY_CRN)
    
    print("Scanning IBM Cloud for the least busy operational quantum processor...")
    # AUTOMATIC TARGETING: Finds the real physical machine with the shortest queue available to your plan
    backend = service.least_busy(operational=True, simulator=False)

print(f"Preparing execution on Backend: {backend.name} | Shots: {NUM_SHOTS} | Theta: {THETA}")

### ============================================================
### CIRCUIT DEFINITIONS (4 qubits to avoid crosstalk)
### q0: Particle | q1: Pointer/Sensor | q2, q3: Isolation
### ============================================================

# Circuit A: Baseline (Pure interferometer)
circuit_a = QuantumCircuit(4, 2)
circuit_a.h(0)
circuit_a.barrier()
circuit_a.h(0)
# Measures only the particle (q0) into classical bit 0 
circuit_a.measure(0, 0)
circuit_a.name = "A_Baseline"

# Circuit B: Strong Measurement (CNOT - Interference destruction)
circuit_b = QuantumCircuit(4, 2)
circuit_b.h(0)
circuit_b.cx(0, 1)
circuit_b.barrier()
circuit_b.h(0)
# Measures BOTH (particle and pointer) to extract Maximum Distinguishability 
circuit_b.measure([0, 1], [0, 1])
circuit_b.name = "B_Strong"

# Circuit R: Noise Calibration (Hardware baseline noise)
circuit_r = QuantumCircuit(4, 2)
# q0 remains in |0> (no superposition). Evaluates gate false positive rate 
circuit_r.cry(THETA, 0, 1) 
circuit_r.barrier()
# Measures BOTH to accurately capture background noise 
circuit_r.measure([0, 1], [0, 1])
circuit_r.name = "R_Noise"

# Circuit C: Weak Measurement (The Crucial Test)
circuit_c = QuantumCircuit(4, 2)
circuit_c.h(0)
circuit_c.cry(THETA, 0, 1) # Interaction with spatial perturbation (pilot wave) 
circuit_c.barrier()
circuit_c.h(0)
# Measures BOTH to evaluate Visibility and Distinguishability simultaneously 
circuit_c.measure([0, 1], [0, 1])
circuit_c.name = "C_Weak"

### ============================================================
### TRANSPILATION AND EXECUTION
### ============================================================
circuits = [circuit_a, circuit_b, circuit_r, circuit_c]

# Optimization Level 3: maximizes hardware efficiency and minimizes intrinsic errors 
pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
optimized_circuits = pm.run(circuits)

# The backend is passed via the 'mode' parameter in SamplerV2
sampler = Sampler(mode=backend)

# Injecting shots into the Sampler options 
sampler.options.default_shots = NUM_SHOTS 

print(f"Sending job to processor {backend.name}...")
job = sampler.run(optimized_circuits)
print(f"Job ID: {job.job_id()}. Waiting for results (This might take a while due to global queue)...")

result = job.result()

### ============================================================
### RAW DATA COLLECTION AND JSON EXPORT
### ============================================================
data = {}
for i, name in enumerate(["A_Baseline", "B_Strong", "R_Noise", "C_Weak"]):
    pub_result = result[i]
    # Correct access to the classical register 'c' in SamplerV2 
    counts = pub_result.data.c.get_counts()
    data[name] = counts
    print(f"\n--- Circuit {name} ---")
    print(f"Counts: {counts}")

# Save ALL results to a physical file for further analysis
file_name = "quantum_experiment_results.json"
with open(file_name, 'w') as json_file:
    json.dump(data, json_file, indent=4)

print(f"\n============================================================")
print(f"SUCCESS! Execution completed on physical hardware: {backend.name}")
print(f"Raw data for the {NUM_SHOTS} shots were successfully recorded")
print(f"in the file: {file_name}")
print(f"============================================================")