### ============================================================
### GHOST INTERFEROMETER: TEST 13 - HIDDEN STRUCTURE
### 1-Million Shot Quantum Randomness & Hidden Variable Test
### ============================================================

import json
import math
import zlib
import numpy as np
from collections import Counter
from qiskit import QuantumCircuit
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

### ============================================================
### CONFIGURATION
### ============================================================
EXECUTION_MODE = "CLOUD"
MY_TOKEN = "KwgGZ3CMazqSPiRTF7gBgoENRS4SbCqcy7C_fIdbqd1-"
MY_CRN = "crn:v1:bluemix:public:quantum-computing:us-east:a/2751423f3df54bf9b963caabf1ceb7e4:e61c405d-5568-4f6b-97dd-0733e1af0fa3::" 

# 1 Million Shots distributed across batches to bypass backend limits
SHOTS_PER_CIRCUIT = 10000
NUM_CIRCUITS = 100  # Total = 1,000,000 shots

if EXECUTION_MODE == "LOCAL":
    from qiskit_ibm_runtime.fake_provider import FakeLimaV2
    backend = FakeLimaV2()
else:
    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=MY_TOKEN, instance=MY_CRN)
    backend = service.least_busy(operational=True, simulator=False)

### ============================================================
### CIRCUIT CONSTRUCTION
### ============================================================
qc = QuantumCircuit(1, 1, name="rng_basis")
qc.h(0)
qc.measure(0, 0)

circuits = [qc] * NUM_CIRCUITS

### ============================================================
### TRANSPILATION & EXECUTION
### ============================================================
pm = generate_preset_pass_manager(optimization_level=1, backend=backend)
opt_circuits = pm.run(circuits)

sampler = Sampler(mode=backend)
sampler.options.default_shots = SHOTS_PER_CIRCUIT

job = sampler.run(opt_circuits)
result = job.result()

### ============================================================
### DATA EXTRACTION (Chronological Shot Sequence)
### ============================================================
raw_sequence = []

for i in range(NUM_CIRCUITS):
    # Extract the exact shot-by-shot bit array from SamplerV2
    # The array shape is (shots, num_classical_bits)
    shot_array = result[i].data.c.array
    # Flatten and convert boolean array to integers 0/1
    raw_sequence.extend(shot_array.flatten().astype(int).tolist())

seq = np.array(raw_sequence, dtype=np.int8)
total_shots = len(seq)

### ============================================================
### RANDOMNESS & HIDDEN STRUCTURE TESTS
### ============================================================
analysis_results = {"total_shots": total_shots}

# 1. Bias (0/1 Distribution)
ones = np.sum(seq)
bias = ones / total_shots
analysis_results["bias"] = bias

# 2. Autocorrelation (Lag 1 to 10)
# Converts sequence to -1 and 1 to find true correlation
seq_bipolar = 2 * seq - 1
autocorr = []
for lag in range(1, 11):
    ac = np.mean(seq_bipolar[:-lag] * seq_bipolar[lag:])
    autocorr.append(ac)
analysis_results["autocorrelation_lags_1_to_10"] = autocorr

# 3. Spectral Analysis (Discrete Fourier Transform)
# Looks for hidden periodicities in the sequence
fft_vals = np.abs(np.fft.rfft(seq_bipolar))
power_spectrum = (fft_vals ** 2) / total_shots
max_power_idx = np.argmax(power_spectrum[1:]) + 1  # ignore DC component
max_power = power_spectrum[max_power_idx]
mean_power = np.mean(power_spectrum[1:])
analysis_results["fourier_max_power_ratio"] = max_power / mean_power

# 4. Block Entropy (Shannon Entropy of 8-bit blocks)
# If randomness is perfect, all 256 states should be equally probable
block_size = 8
num_blocks = total_shots // block_size
blocks = np.packbits(seq[:num_blocks * block_size].reshape(-1, block_size), axis=1).flatten()
counts = Counter(blocks)
probs = np.array(list(counts.values())) / num_blocks
entropy = -np.sum(probs * np.log2(probs))
analysis_results["block_entropy_8bit"] = entropy
analysis_results["ideal_entropy_8bit"] = 8.0

# 5. Lempel-Ziv / Algorithmic Complexity (Compression Ratio Proxy)
# Perfect randomness is incompressible. 
# We use zlib compression ratio on the packed bytes as a proxy for algorithmic structure.
byte_data = np.packbits(seq).tobytes()
compressed_data = zlib.compress(byte_data, level=9)
compression_ratio = len(compressed_data) / len(byte_data)
analysis_results["lz_compression_ratio"] = compression_ratio

with open("hidden_structure_results.json", "w") as f:
    json.dump(analysis_results, f, indent=4)

### ============================================================
### THEORETICAL VERDICT
### ============================================================
print(f"\n=== HIDDEN STRUCTURE ANALYSIS VERDICT ===")
print(f"Total Measurements: {total_shots}")
print(f"Bias (Ideal = 0.5): {bias:.5f}")
print(f"Max Autocorrelation (Lags 1-10): {max(np.abs(autocorr)):.5f}")
print(f"Fourier Max-to-Mean Power Ratio (Ideal ~ 1.0): {max_power / mean_power:.2f}")
print(f"Shannon Block Entropy (Ideal = 8.0): {entropy:.4f} bits")
print(f"Algorithmic Incompressibility (Ideal >= 1.0): {compression_ratio:.4f}")

# Strict Thresholds for Quantum Randomness Violation
is_biased = abs(bias - 0.5) > (5 / math.sqrt(total_shots)) # 5-sigma bounds
has_memory = max(np.abs(autocorr)) > (5 / math.sqrt(total_shots))
is_compressible = compression_ratio < 0.99

if is_biased or has_memory or is_compressible:
    print("\n[!] HIDDEN STRUCTURE DETECTED: The sequence deviates from perfect randomness.")
    print("The system demonstrates memory, algorithmic compressibility, or deterministic bias.")
    print("This supports Einstein's intuition: quantum randomness is a manifestation of underlying hidden variables.")
else:
    print("\n[-] COPENHAGEN CONFIRMED: The sequence is algorithmically and statistically structureless.")
    print("No hidden variables or historical memory found. The wavefunction collapse appears perfectly irreducible.")