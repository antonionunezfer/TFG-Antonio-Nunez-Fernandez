from gurobipy import GRB, Model, quicksum
import matplotlib.pyplot as plt


ruta_archivo = 'VFR10_5_1_Gap.txt'
print(f"Procesando: {ruta_archivo}")

with open(ruta_archivo) as f:
    lineas = f.readlines()

trabajos, maquinas = map(int, lineas[0].split())

p = []
for i in range(1, trabajos + 1):
    valores = list(map(int, lineas[i].split()))
    tiempos = [valores[j + 1] for j in range(0, len(valores), 2)]
    p.append(tiempos)

posiciones=trabajos

# Crear modelo
Modelo_posiciones = Model("Modelo_posiciones")

Modelo_posiciones.setParam(GRB.Param.TimeLimit, 3600)

# --- Variables de decisión ---
# β_ik: binaria, 1 si el trabajo i corresponde a la posición k, 0 en caso contrario.
β = Modelo_posiciones.addVars(trabajos, posiciones, vtype=GRB.BINARY, name="beta")

# C_kj: tiempo de finalización de la posicion k en la maquina j.
C = Modelo_posiciones.addVars(posiciones, maquinas, lb=0, vtype=GRB.CONTINUOUS, name="C")

# C_kj: tiempo de finalización de la posicion k en la maquina j.
CC = Modelo_posiciones.addVars(trabajos, maquinas, lb=0, vtype=GRB.CONTINUOUS, name="CC")

# --- Restricciones ---------------------------------
#---------------------------------------------------------
for i in range(trabajos):
    Modelo_posiciones.addConstr(quicksum(β[i, k] for k in range(posiciones)) == 1)

#-----------------------------------------------
for k in range(posiciones):
    Modelo_posiciones.addConstr(quicksum(β[i, k] for i in range(trabajos)) == 1)

#-----------------------------------------------
Modelo_posiciones.addConstr(C[0, 0] == quicksum(p[i][0] * β[i, 0] for i in range(trabajos)))
#-------------------------------------------
for k in range(1, posiciones):
    Modelo_posiciones.addConstr(C[k, 0] >= C[k-1, 0] + quicksum(p[i][0] * β[i, k] for i in range(trabajos)))

for k in range(posiciones):    
    for j in range(1, maquinas):
        Modelo_posiciones.addConstr(C[k, j] >= C[k, j-1] + quicksum(p[i][j] * β[i, k] for i in range(trabajos)))

for k in range(1, posiciones):    
    for j in range(1, maquinas):
        Modelo_posiciones.addConstr(C[k, j] >= C[k-1, j] + quicksum(p[i][j] * β[i, k] for i in range(trabajos)))


ultima_maquina = maquinas - 1

# --- Función objetivo: Minimizar sumatorio (C[i,última_máquina])
Modelo_posiciones.setObjective(quicksum(C[k, ultima_maquina] for k in range(posiciones)), GRB.MINIMIZE)

# --- Resolver el modelo ---
Modelo_posiciones.optimize()

# ----------------------------- RESULTADOS -------------------------
if Modelo_posiciones.status in [GRB.OPTIMAL, GRB.TIME_LIMIT]:
    # El GAP se obtiene con el atributo .MIPGap (se multiplica por 100 para porcentaje)
    gap_actual = Modelo_posiciones.MIPGap * 100
    mejor_limite_inferior = Modelo_posiciones.ObjBound
    
    print("\n" + "="*40)
    print(" RESULTADOS DE LA OPTIMIZACIÓN")
    print("="*40)
    print(f"Estado: {Modelo_posiciones.status}")
    print(f"Valor Objetivo (Z): {Modelo_posiciones.objVal:.2f}")
    print(f"Mejor Límite Inferior: {mejor_limite_inferior:.2f}")
    print(f"GAP Relativo: {gap_actual:.2f}%")
    print("="*40)

    # ------------------ DIAGRAMA DE GANTT -------------------------
    fig, ax = plt.subplots(figsize=(12, 6))
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
    ax.set_title(f'Gantt: {ruta_archivo} | Obj: {Modelo_posiciones.objVal:.2f} | Gap: {gap_actual:.2f}%')
    ax.set_yticks(range(maquinas))
    ax.set_yticklabels([f'M{j}' for j in range(maquinas)])
    ax.grid(True, axis='x', linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    plt.show()

elif Modelo_posiciones.status == GRB.INFEASIBLE:
    print("El modelo es infactible. Revisa las restricciones.")
else:
    print(f"Proceso finalizado sin solución óptima. Status: {Modelo_posiciones.status}") 
  

    
