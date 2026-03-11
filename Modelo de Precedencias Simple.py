from gurobipy import GRB, Model, quicksum
import matplotlib.pyplot as plt

ruta_archivo = 'VFR10_5_1_Gap.txt'


with open(ruta_archivo) as f:
    lineas = f.readlines()

trabajos, maquinas = map(int, lineas[0].split())
p = []
for i in range(1, trabajos + 1):
    valores = list(map(int, lineas[i].split()))
    tiempos = [valores[j + 1] for j in range(0, len(valores), 2)]
    p.append(tiempos)

# CORRECCIÓN: Usar sum() de Python para constantes, no quicksum()
M = sum(p[i][j] for i in range(trabajos) for j in range(maquinas))

Modelo_precedencias = Model("Modelo_precedencias")
Modelo_precedencias.setParam(GRB.Param.TimeLimit, 3600)

# --- Variables de decisión ---
alfa = Modelo_precedencias.addVars(trabajos, trabajos, vtype=GRB.BINARY, name="alfa")
C = Modelo_precedencias.addVars(trabajos, maquinas, lb=0, vtype=GRB.CONTINUOUS, name="C")

# --- Restricciones ---
# 1. Todo par de trabajos tiene un orden de precedencia
for i in range(trabajos):
    for k in range(i + 1, trabajos):
        Modelo_precedencias.addConstr(alfa[i, k] + alfa[k, i] == 1, name=f"prec_{i}_{k}")

# 2. Tiempo en la primera máquina
for i in range(trabajos):
    Modelo_precedencias.addConstr(
        C[i, 0] >= quicksum(p[k][0] * alfa[k, i] for k in range(trabajos) if k != i) + p[i][0],
        name=f"maquina_0_trabajo_{i}"
    )

# 3. Restricciones disyuntivas para evitar solapamientos
for i in range(trabajos):
    for k in range(trabajos):
        if i != k:
            for j in range(maquinas):
                Modelo_precedencias.addConstr(
                    C[k, j] >= C[i, j] + p[k][j] * alfa[i, k] - M * (1 - alfa[i, k]),
                    name=f"disyuntiva_{i}_{k}_{j}"
                )
            
# 4. Secuencia de un mismo trabajo en las diferentes máquinas
for i in range(trabajos):
    for j in range(1, maquinas):
        Modelo_precedencias.addConstr(
            C[i, j] >= C[i, j-1] + p[i][j], 
            name=f"secuencia_{i}_{j}"
        )

# --- Función objetivo ---
ultima_maquina = maquinas - 1
Modelo_precedencias.setObjective(
    quicksum(C[i, ultima_maquina] for i in range(trabajos)), 
    GRB.MINIMIZE
)

# --- Resolver el modelo ---
Modelo_precedencias.optimize()

# --- Resultados y GAP ---
if Modelo_precedencias.status in [GRB.OPTIMAL, GRB.TIME_LIMIT]:
    # El GAP se obtiene con el atributo .MIPGap (se multiplica por 100 para porcentaje)
    gap_actual = Modelo_precedencias.MIPGap * 100
    mejor_limite_inferior = Modelo_precedencias.ObjBound
    
    print("\n" + "="*40)
    print(" RESULTADOS DE LA OPTIMIZACIÓN")
    print("="*40)
    print(f"Estado: {Modelo_precedencias.status}")
    print(f"Valor Objetivo (Z): {Modelo_precedencias.objVal:.2f}")
    print(f"Mejor Límite Inferior: {mejor_limite_inferior:.2f}")
    print(f"GAP Relativo: {gap_actual:.2f}%")
    print("="*40)

    # --- Dibujar Diagrama de Gantt ---
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Generar paleta de colores fija para que cada trabajo sea distinguible
    cmap = plt.get_cmap('tab20') 
    
    for i in range(trabajos):
        for j in range(maquinas):
            finalizacion = C[i, j].X
            duracion = p[i][j]
            inicio = finalizacion - duracion
            
            # Dibujar bloque de la tarea
            color = cmap(i % 20)
            ax.broken_barh([(inicio, duracion)], (j - 0.4, 0.8), 
                          facecolors=color, edgecolor='black', alpha=0.8)
            
            # Texto descriptivo: "T[índice]"
            ax.text(inicio + duracion/2, j, f'T{i}', 
                    ha='center', va='center', color='white', weight='bold', fontsize=9)

    # Configuración estética del gráfico
    ax.set_xlabel('Tiempo (unidades)')
    ax.set_ylabel('Máquinas')
    ax.set_title(f'Gantt: {ruta_archivo} | Obj: {Modelo_precedencias.objVal:.2f} | Gap: {gap_actual:.2f}%')
    ax.set_yticks(range(maquinas))
    ax.set_yticklabels([f'M{j}' for j in range(maquinas)])
    ax.grid(True, axis='x', linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    plt.show()

elif Modelo_precedencias.status == GRB.INFEASIBLE:
    print("El modelo es infactible. Revisa las restricciones.")
else:
    print(f"Proceso finalizado sin solución óptima. Status: {Modelo_precedencias.status}")





