import matplotlib.pyplot as plt
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter

# Configuração visual para o estilo da revista
style = {
    "backgroundcolor": "#ffffff",
    "fontsize": 12,
    "subfontsize": 10,
    "displaycolor": {
        "h": ("#ee7733", "#ffffff"),
        "x": ("#cc3311", "#ffffff"),
        "p": ("#0077bb", "#ffffff"),
        "cry": ("#009988", "#ffffff"),
        "measure": ("#000000", "#ffffff")
    }
}

# Usando objetos Parameter para o Qiskit renderizar os símbolos em LaTeX
THETA = Parameter(r"$\theta$")
PHI = Parameter(r"$\phi$")

def build_quadrant_circuits():
    circuits = {}
    
    # --------------------------------------------------------------
    # 1. STD-FORWARD: Sensor A (q1) precede Sensor B (q2)
    # --------------------------------------------------------------
    qc_std_fwd = QuantumCircuit(3, 2, name="(a) Standard Forward")
    qc_std_fwd.h(0)
    qc_std_fwd.barrier()
    qc_std_fwd.cry(THETA, 0, 1)      # Sensor A (Tempo 1)
    qc_std_fwd.barrier()
    qc_std_fwd.p(PHI, 0)      
    qc_std_fwd.barrier()
    qc_std_fwd.x(0)
    qc_std_fwd.cry(THETA, 0, 2)      # Sensor B (Tempo 2)
    qc_std_fwd.x(0)
    qc_std_fwd.barrier()
    qc_std_fwd.h(0)
    qc_std_fwd.measure([1, 2], [0, 1])
    circuits["std_fwd"] = qc_std_fwd

    # --------------------------------------------------------------
    # 2. STD-REVERSE: Sensor B (q2) precede Sensor A (q1)
    # --------------------------------------------------------------
    qc_std_rev = QuantumCircuit(3, 2, name="(b) Standard Reverse")
    qc_std_rev.h(0)
    qc_std_rev.barrier()
    qc_std_rev.x(0)
    qc_std_rev.cry(THETA, 0, 2)      # Sensor B (Tempo 1)
    qc_std_rev.x(0)
    qc_std_rev.barrier()
    qc_std_rev.p(PHI, 0)      
    qc_std_rev.barrier()
    qc_std_rev.cry(THETA, 0, 1)      # Sensor A (Tempo 2)
    qc_std_rev.barrier()
    qc_std_rev.h(0)
    qc_std_rev.measure([1, 2], [0, 1])
    circuits["std_rev"] = qc_std_rev

    # --------------------------------------------------------------
    # 3. SWAP-FORWARD: Sensor A (q2) precede Sensor B (q1)
    # --------------------------------------------------------------
    qc_swap_fwd = QuantumCircuit(3, 2, name="(c) Swapped Forward")
    qc_swap_fwd.h(0)
    qc_swap_fwd.barrier()
    qc_swap_fwd.cry(THETA, 0, 2)     # Sensor A (Tempo 1)
    qc_swap_fwd.barrier()
    qc_swap_fwd.p(PHI, 0)
    qc_swap_fwd.barrier()
    qc_swap_fwd.x(0)
    qc_swap_fwd.cry(THETA, 0, 1)     # Sensor B (Tempo 2)
    qc_swap_fwd.x(0)
    qc_swap_fwd.barrier()
    qc_swap_fwd.h(0)
    qc_swap_fwd.measure([1, 2], [0, 1])
    circuits["swap_fwd"] = qc_swap_fwd

    # --------------------------------------------------------------
    # 4. SWAP-REVERSE: Sensor B (q1) precede Sensor A (q2)
    # --------------------------------------------------------------
    qc_swap_rev = QuantumCircuit(3, 2, name="(d) Swapped Reverse")
    qc_swap_rev.h(0)
    qc_swap_rev.barrier()
    qc_swap_rev.x(0)
    qc_swap_rev.cry(THETA, 0, 1)     # Sensor B (Tempo 1)
    qc_swap_rev.x(0)
    qc_swap_rev.barrier()
    qc_swap_rev.p(PHI, 0)
    qc_swap_rev.barrier()
    qc_swap_rev.cry(THETA, 0, 2)     # Sensor A (Tempo 2)
    qc_swap_rev.barrier()
    qc_swap_rev.h(0)
    qc_swap_rev.measure([1, 2], [0, 1])
    circuits["swap_rev"] = qc_swap_rev
    
    return circuits

# ==========================================
# GERAÇÃO DA IMAGEM CONSOLIDADA (2x2)
# ==========================================
circuits = build_quadrant_circuits()

# Prepara a figura principal
fig = plt.figure(figsize=(16, 10))

# Mapeia as posições no grid 2x2
layout = {
    "std_fwd":  (2, 2, 1),
    "std_rev":  (2, 2, 2),
    "swap_fwd": (2, 2, 3),
    "swap_rev": (2, 2, 4)
}

for key, pos in layout.items():
    ax = fig.add_subplot(*pos)
    qc = circuits[key]
    
    # Desenha o circuito no eixo correspondente
    qc.draw(output='mpl', ax=ax, style=style, scale=0.85, 
            idle_wires=False, fold=-1, plot_barriers=True)
    
    # Define o título do sub-gráfico
    ax.set_title(qc.name, fontsize=16, fontweight='bold', pad=10)

plt.tight_layout(pad=3.0)

# Salva a imagem nos formatos PNG (para LaTeX) e PDF
plt.savefig("absolute_control_quadrant.png", format="png", dpi=300, bbox_inches="tight")
plt.savefig("absolute_control_quadrant.pdf", format="pdf", bbox_inches="tight")
print("Gráficos salvos com sucesso como 'absolute_control_quadrant.png' e 'absolute_control_quadrant.pdf'")

plt.show()