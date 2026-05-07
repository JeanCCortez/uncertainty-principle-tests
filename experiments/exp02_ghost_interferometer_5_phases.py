### ============================================================
### GHOST INTERFEROMETER: ASYMMETRY AND WEAK EXCITATION TEST
### Execution Plan on the IBM Quantum Platform
### ============================================================

import json
import math
from qiskit import QuantumCircuit
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

### ============================================================
### EXECUTION MODE CONTROLLER
### ============================================================
EXECUTION_MODE = "CLOUD"  # Mantenha "CLOUD" para rodar o tiro real

### ============================================================
### BACKEND CONFIGURATION
### ============================================================
MY_TOKEN = "YOUR_TOKEN_HERE"
MY_CRN = "YOUR_CRN_HERE" 

NUM_SHOTS = 8192
THETA = 0.2  # Ângulo fraco de interação térmica/excitação

# Array de varredura de fase (phi) de 0 até Pi
PHASES = [0, math.pi/4, math.pi/2, 3*math.pi/4, math.pi]
PHASE_NAMES = ["0", "pi_4", "pi_2", "3pi_4", "pi"]

# Autenticação e Busca Automática da menor fila
if EXECUTION_MODE == "LOCAL":
    print("Initializing LOCAL simulator (Fake 5-Qubit Chip bypassing limit)...")
    from qiskit_ibm_runtime.fake_provider import FakeLimaV2
    backend = FakeLimaV2()
else:
    print("Authenticating with IBM Cloud (Real Hardware)...")
    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=MY_TOKEN, instance=MY_CRN)
    print("Scanning IBM Cloud for the least busy operational quantum processor...")
    backend = service.least_busy(operational=True, simulator=False)

print(f"Preparing execution on Backend: {backend.name} | Shots: {NUM_SHOTS}")

### ============================================================
### CIRCUIT DEFINITIONS (Vaníček-Mello Algorithm)
### q0: Particle | q1: Sensor Path A | q2: Sensor Path B
### ============================================================
circuits = []

for phi, name in zip(PHASES, PHASE_NAMES):
    # Inicializa circuito com 3 qubits e 3 bits clássicos
    qc = QuantumCircuit(3, 3)
    qc.name = f"Ghost_Interf_{name}"
    
    # 1. Cria a superposição da partícula
    qc.h(0)
    
    # 2. Sensor A vigia o Caminho A (ativado se q0 = |1>)
    qc.cry(THETA, 0, 1)
    
    # 3. Varredura de fase inserida no Caminho A
    qc.p(phi, 0)
    
    # 4. Sensor B vigia o Caminho B (A Sombra)
    # CORREÇÃO FÍSICA: Inverte a lógica de q0 temporariamente para ler o estado |0>
    qc.x(0)
    qc.cry(THETA, 0, 2)
    qc.x(0)
    
    # 5. Recombinação do Interferômetro
    qc.h(0)
    
    # 6. Medimos TUDO: Partícula(q0), Sensor A(q1), e Sensor B(q2) simultaneamente
    qc.measure([0, 1, 2], [0, 1, 2])
    
    circuits.append(qc)

### ============================================================
### TRANSPILATION AND EXECUTION
### ============================================================
# Optimization Level 3 para redução máxima de erros das portas lógicas
pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
optimized_circuits = pm.run(circuits)

sampler = Sampler(mode=backend)
sampler.options.default_shots = NUM_SHOTS 

print(f"Sending ghost-interferometer suite to processor {backend.name}...")
job = sampler.run(optimized_circuits)
print(f"Job ID: {job.job_id()}. Waiting for results (This might take a while)...")

result = job.result()

### ============================================================
### RAW DATA COLLECTION AND JSON EXPORT
### ============================================================
data = {}
for i, name in enumerate(PHASE_NAMES):
    pub_result = result[i]
    counts = pub_result.data.c.get_counts()
    data[f"Phi_{name}"] = counts
    print(f"\n--- Phase: {name} ---")
    print(f"Counts: {counts}")

file_name = "ghost_interferometer_results.json"
with open(file_name, 'w') as json_file:
    json.dump(data, json_file, indent=4)

print(f"\n============================================================")
print(f"SUCCESS! Execution completed on physical hardware: {backend.name}")
print(f"Raw data mapped across 5 phases and recorded in: {file_name}")
print(f"============================================================")