from gurobipy import GRB, Model, quicksum
import pandas as pd
import os

# --- Configuración de rutas ---
carpeta_instancias = '..\..\DATOS\FASE1'
archivo_excel = 'Resultados_Posiciones_Con_Pesos.xlsx' # Nombre específico para este modelo

# Obtener solo los archivos .txt de la carpeta
archivos_txt = [f for f in os.listdir(carpeta_instancias) if f.endswith('.txt')]
total_instancias = len(archivos_txt)

# Variable para guardar el tiempo de la instancia anterior
tiempo_anterior = None

print("\n" + "⭐"*30)
print(f"🚀 INICIANDO LOTE (POSICIONES CON PESOS): {total_instancias} instancias detectadas")
print("⭐"*30 + "\n")

# Bucle para procesar cada instancia
for indice, nombre_archivo in enumerate(archivos_txt, start=1):
    ruta_archivo = os.path.join(carpeta_instancias, nombre_archivo)
    faltan = total_instancias - indice
    
    # --- 🖥️ PRINTS VISUALES DE PROGRESO 🖥️ ---
    print("="*60)
    print(f"📂 INSTANCIA ACTUAL : {nombre_archivo}")
    print(f"📊 PROGRESO         : [ {indice} / {total_instancias} ] -> Faltan {faltan}")
    
    if tiempo_anterior is not None:
        print(f"⏱️  TIEMPO ANTERIOR  : {tiempo_anterior:.2f} segundos")
    else:
        print(f"⏱️  TIEMPO ANTERIOR  : N/A (Esta es la primera)")
    print("="*60)

    # --- Lectura de datos ---
    with open(ruta_archivo) as f:
        lineas = f.readlines()

    trabajos, maquinas = map(int, lineas[0].split())

    p = []
    for i in range(1, trabajos + 1):
        valores = list(map(int, lineas[i].split()))
        tiempos = [valores[j + 1] for j in range(0, len(valores), 2)]
        p.append(tiempos)
        
    w = [int(k.strip()) for k in lineas[-trabajos:]]

    posiciones = trabajos
    M = sum(p[i][j] for i in range(trabajos) for j in range(maquinas))

    # --- Configuración del Modelo ---
    Modelo_posiciones_con_pesos = Model("Modelo_posiciones_con_pesos")
    Modelo_posiciones_con_pesos.setParam(GRB.Param.TimeLimit, 3600)
    Modelo_posiciones_con_pesos.setParam('OutputFlag', 0)  # Gurobi en modo silencioso

    # --- Variables de decisión ---
    beta = Modelo_posiciones_con_pesos.addVars(trabajos, posiciones, vtype=GRB.BINARY, name="beta")
    C = Modelo_posiciones_con_pesos.addVars(posiciones, maquinas, lb=0, vtype=GRB.CONTINUOUS, name="C")
    CC = Modelo_posiciones_con_pesos.addVars(trabajos, maquinas, lb=0, vtype=GRB.CONTINUOUS, name="CC")

    # --- Restricciones ---
    for i in range(trabajos):
        Modelo_posiciones_con_pesos.addConstr(quicksum(beta[i, k] for k in range(posiciones)) == 1)

    for k in range(posiciones):
        Modelo_posiciones_con_pesos.addConstr(quicksum(beta[i, k] for i in range(trabajos)) == 1)

    Modelo_posiciones_con_pesos.addConstr(C[0, 0] == quicksum(p[i][0] * beta[i, 0] for i in range(trabajos)))

    for k in range(1, posiciones):
        Modelo_posiciones_con_pesos.addConstr(C[k, 0] >= C[k-1, 0] + quicksum(p[i][0] * beta[i, k] for i in range(trabajos)))

    for k in range(posiciones):    
        for j in range(1, maquinas):
            Modelo_posiciones_con_pesos.addConstr(C[k, j] >= C[k, j-1] + quicksum(p[i][j] * beta[i, k] for i in range(trabajos)))

    for k in range(1, posiciones):    
        for j in range(1, maquinas):
            Modelo_posiciones_con_pesos.addConstr(C[k, j] >= C[k-1, j] + quicksum(p[i][j] * beta[i, k] for i in range(trabajos)))

    ultima_maquina = maquinas - 1

    for i in range(trabajos):
        for k in range(posiciones):
            Modelo_posiciones_con_pesos.addConstr(CC[i, ultima_maquina] >= C[k, ultima_maquina] - M * (1 - beta[i, k]))

    # --- Función objetivo ---
    Modelo_posiciones_con_pesos.setObjective(quicksum(w[i] * CC[i, ultima_maquina] for i in range(trabajos)), GRB.MINIMIZE)

    # --- Resolver el modelo ---
    Modelo_posiciones_con_pesos.optimize()

    # --- Exportación a Excel y actualización de tiempo ---
    if Modelo_posiciones_con_pesos.status in [GRB.OPTIMAL, GRB.TIME_LIMIT]:
        tiempo_anterior = Modelo_posiciones_con_pesos.Runtime
        gap_actual = Modelo_posiciones_con_pesos.MIPGap * 100
        
        nuevo_registro = pd.DataFrame({
            'Instancia': [nombre_archivo],
            'Mejor Solucion (Z)': [Modelo_posiciones_con_pesos.objVal],
            'Tiempo (segundos)': [tiempo_anterior],
            'GAP (%)': [gap_actual]
        })
        
        if os.path.exists(archivo_excel):
            df_existente = pd.read_excel(archivo_excel)
            df_final = pd.concat([df_existente, nuevo_registro], ignore_index=True)
        else:
            df_final = nuevo_registro
            
        df_final.to_excel(archivo_excel, index=False)
        print(f"  ✅ Completado. Guardado en Excel con un GAP del {gap_actual:.2f}%\n")
    else:
        print(f"  ⚠️ La instancia no encontró solución. Estado: {Modelo_posiciones_con_pesos.status}\n")
        tiempo_anterior = Modelo_posiciones_con_pesos.Runtime if hasattr(Modelo_posiciones_con_pesos, 'Runtime') else 0
    
    # --- Liberar memoria ---
    Modelo_posiciones_con_pesos.dispose()


print("\n🎉 ¡PROCESO TOTALMENTE FINALIZADO! Revisa tu archivo Excel.")
