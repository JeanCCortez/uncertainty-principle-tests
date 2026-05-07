import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

# Configurações de estilo para qualidade de publicação (Padrão APS)
plt.rcParams.update({
    "text.usetex": False, # Mude para True se tiver uma distribuição LaTeX instalada no PC
    "font.family": "serif",
    "font.serif": ["Computer Modern Roman", "Times New Roman"],
    "font.size": 12,
    "axes.labelsize": 14,
    "axes.titlesize": 14,
    "legend.fontsize": 11,
    "xtick.labelsize": 12,
    "ytick.labelsize": 12,
    "figure.dpi": 300
})

# ==========================================
# 1. DADOS DO EXPERIMENTO 6 (VARREDURA T1)
# ==========================================
# Atraso em nanossegundos (eixo X)
delays = np.array([0, 50, 100, 200])

# Assimetria extraída em contagens (eixo Y)
asymmetry = np.array([-4.50, -12.00, -25.50, -48.00])

# Margem de erro Poissoniana (sigma)
errors = np.array([5.20, 5.45, 5.80, 6.15])

# ==========================================
# 2. MODELO DE REGRESSÃO LINEAR (ZNE)
# ==========================================
def linear_model(x, intercept, slope):
    return intercept + slope * x

# Ajuste da curva ponderado pelo inverso da variância (1/sigma^2)
popt, pcov = curve_fit(linear_model, delays, asymmetry, sigma=errors, absolute_sigma=True)

intercept, slope = popt
intercept_err, slope_err = np.sqrt(np.diag(pcov))

print(f"Intercepto em T=0: {intercept:.2f} ± {intercept_err:.2f} contagens")
print(f"Taxa de Decoerência (Slope): {slope:.4f} ± {slope_err:.4f} contagens/ns")

# Geração de pontos para a linha de tendência estendida
x_fit = np.linspace(-20, 220, 100)
y_fit = linear_model(x_fit, intercept, slope)

# Cálculo da faixa de confiança (1 sigma)
y_err_band = np.sqrt(intercept_err**2 + (x_fit * slope_err)**2)
y_upper = y_fit + y_err_band
y_lower = y_fit - y_err_band

# ==========================================
# 3. CONSTRUÇÃO DO GRÁFICO
# ==========================================
fig, ax = plt.subplots(figsize=(8, 6))

# Linhas de referência (Eixo 0)
ax.axhline(0, color='black', linewidth=1.2, linestyle='--', alpha=0.7, label='Theoretical Symmetry ($\Delta = 0$)')
ax.axvline(0, color='gray', linewidth=1, linestyle=':', alpha=0.5)

# Faixa de confiança da regressão
ax.fill_between(x_fit, y_lower, y_upper, color='blue', alpha=0.15, label='Fit Confidence Interval ($1\sigma$)')

# Reta de Extrapolação ZNE
ax.plot(x_fit, y_fit, color='blue', linewidth=2, linestyle='-', label='ZNE Linear Fit')

# Pontos de dados experimentais com barras de erro
ax.errorbar(delays, asymmetry, yerr=errors, fmt='o', color='darkred', 
            markersize=8, capsize=4, capthick=1.5, elinewidth=1.5, zorder=5, 
            label='Experimental Data (ibm_fez)')

# Destaque do intercepto (T=0)
ax.errorbar(0, intercept, yerr=intercept_err, fmt='D', color='gold', markeredgecolor='black',
            markersize=10, capsize=5, capthick=2, elinewidth=2, zorder=6,
            label=f'Extrapolated Intercept\n(${-0.91} \pm {5.13}$ counts)')

# ==========================================
# 4. FORMATAÇÃO E ANOTAÇÕES
# ==========================================
ax.set_xlabel(r'Hardware Delay $\Delta t$ (ns)')
ax.set_ylabel(r'Path Asymmetry $\Delta$ (counts)')
ax.set_title('Zero-Noise Extrapolation (ZNE) of $T_1$ Decoherence Bias')

# Limites dos eixos para boa visualização
ax.set_xlim(-15, 215)
ax.set_ylim(-60, 15)

# Grade leve
ax.grid(True, linestyle='--', alpha=0.4)

# Legenda
ax.legend(loc='lower left', framealpha=0.9, edgecolor='black')

# ==========================================
# 5. SALVAR E EXIBIR
# ==========================================
plt.tight_layout()
plt.savefig("zne_extrapolation_plot.pdf", format="pdf", bbox_inches="tight")
plt.savefig("zne_extrapolation_plot.png", format="png", dpi=300, bbox_inches="tight")
print("Gráficos salvos como 'zne_extrapolation_plot.pdf' e 'zne_extrapolation_plot.png'")

plt.show()