from qiskit_ibm_runtime import QiskitRuntimeService
import datetime

MEU_TOKEN = "YOUR TOKEN"

service = QiskitRuntimeService(channel="ibm_quantum_platform", token=MEU_TOKEN)
backend = service.backend("ibm_fez")

# Definindo a data do seu teste (6 de Maio de 2026)
data_do_teste = datetime.datetime(2026, 5, 6)

print(f"Conectando ao {backend.name} e baixando calibração histórica...")
propriedades = backend.properties(datetime=data_do_teste)

tempos_t1 = []

# Varredura segura com tratamento de falhas do hardware
for q in range(backend.num_qubits):
    try:
        t1 = propriedades.t1(q)
        tempos_t1.append(t1)
    except Exception:
        # Se o qubit falhou na calibração no dia do teste, ignoramos.
        print(f"Aviso: Qubit {q} inativo ou com falha de leitura no dia. Ignorado da média.")
        continue

# Calcula a média apenas dos qubits operacionais
t1_medio = sum(tempos_t1) / len(tempos_t1) * 1e6 # Convertendo para microssegundos

print(f"\n============================================================")
print(f"T1 médio dos qubits operacionais no {backend.name}")
print(f"Data: {data_do_teste.date()}: {t1_medio:.2f} µs")
print(f"============================================================")