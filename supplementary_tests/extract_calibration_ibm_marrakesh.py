from qiskit_ibm_runtime import QiskitRuntimeService
import datetime

MEU_TOKEN = "YOUR TOKEN"

service = QiskitRuntimeService(channel="ibm_quantum_platform", token=MEU_TOKEN)
backend = service.backend("ibm_marrakesh")

# A data em que você rodou os testes
data_do_teste = datetime.datetime(2026, 5, 6)

print(f"Conectando ao {backend.name} e baixando calibração histórica...")
propriedades = backend.properties(datetime=data_do_teste)

tempos_t1 = []
erros_2q = [] # Renomeado para abranger qualquer porta de emaranhamento nativa

# 1. Varredura do T1 médio (com proteção)
for q in range(backend.num_qubits):
    try:
        t1 = propriedades.t1(q)
        tempos_t1.append(t1)
    except Exception:
        continue

# 2. Varredura do Erro Médio das portas de 2 qubits (cx, ecr ou cz)
for gate in propriedades.gates:
    # A busca agora captura a porta nativa, não importa qual arquitetura a IBM use
    if gate.gate in ['cx', 'ecr', 'cz']: 
        for param in gate.parameters:
            if param.name == 'gate_error':
                erros_2q.append(param.value)

# Cálculos com trava de segurança (evita o ZeroDivisionError)
t1_medio = (sum(tempos_t1) / len(tempos_t1) * 1e6) if len(tempos_t1) > 0 else 0
erro_2q_medio = (sum(erros_2q) / len(erros_2q) * 100) if len(erros_2q) > 0 else 0

print(f"\n============================================================")
print(f"Métricas do {backend.name} em {data_do_teste.date()}:")
print(f"T1 médio operacional: {t1_medio:.2f} µs")
print(f"Erro médio em portas de emaranhamento: {erro_2q_medio:.3f} %")
print(f"============================================================")