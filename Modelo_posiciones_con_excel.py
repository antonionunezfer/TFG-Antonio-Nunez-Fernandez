from gurobipy import GRB, Model, quicksum
import pandas as pd
import os

# --- Configuración de rutas ---
carpeta_instancias = '..\..\DATOS\FASE1'
archivo_excel = 'Resultados_Posiciones.xlsx' # Nombre para el modelo de posiciones

# Obtener solo los archivos .txt de la carpeta
archivos_txt = [f for f in os.listdir(carpeta_instancias) if f.endswith('.txt')]
total_instancias = len(archivos_txt)

# Variable para guardar el tiempo de la instancia anterior
tiempo_anterior = None

print("\n" + "⭐"*30)
print(f"🚀 INICIANDO LOTE (MODELO POSICIONES): {total_instancias} instancias detectadas")
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

    posiciones = trabajos

    # --- Configuración del Modelo ---
    Modelo_posiciones = Model("Modelo_posiciones")
    Modelo_posiciones.setParam(GRB.Param.TimeLimit, 3600)
    Modelo_posiciones.setParam('OutputFlag', 0)  # Gurobi en modo silencioso

    # --- Variables de decisión ---
    β = Modelo_posiciones.addVars(trabajos, posiciones, vtype=GRB.BINARY, name="beta")
    C = Modelo_posiciones.addVars(posiciones, maquinas, lb=0, vtype=GRB.CONTINUOUS, name="C")
    CC = Modelo_posiciones.addVars(trabajos, maquinas, lb=0, vtype=GRB.CONTINUOUS, name="CC")

    # --- Restricciones ---
    for i in range(trabajos):
        Modelo_posiciones.addConstr(quicksum(β[i, k] for k in range(posiciones)) == 1)

    for k in range(posiciones):
        Modelo_posiciones.addConstr(quicksum(β[i, k] for i in range(trabajos)) == 1)

    Modelo_posiciones.addConstr(C[0, 0] == quicksum(p[i][0] * β[i, 0] for i in range(trabajos)))

    for k in range(1, posiciones):
        Modelo_posiciones.addConstr(C[k, 0] >= C[k-1, 0] + quicksum(p[i][0] * β[i, k] for i in range(trabajos)))

    for k in range(posiciones):    
        for j in range(1, maquinas):
            Modelo_posiciones.addConstr(C[k, j] >= C[k, j-1] + quicksum(p[i][j] * β[i, k] for i in range(trabajos)))

    for k in range(1, posiciones):    
        for j in range(1, maquinas):
            Modelo_posiciones.addConstr(C[k, j] >= C[k-1, j] + quicksum(p[i][j] * β[i, k] for i in range(trabajos)))

    # --- Función objetivo ---
    ultima_maquina = maquinas - 1
    Modelo_posiciones.setObjective(quicksum(C[k, ultima_maquina] for k in range(posiciones)), GRB.MINIMIZE)

    # --- Resolver el modelo ---
    Modelo_posiciones.optimize()

    # --- Exportación a Excel y actualización de tiempo ---
    if Modelo_posiciones.status in [GRB.OPTIMAL, GRB.TIME_LIMIT]:
        tiempo_anterior = Modelo_posiciones.Runtime
        gap_actual = Modelo_posiciones.MIPGap * 100
        
        nuevo_registro = pd.DataFrame({
            'Instancia': [nombre_archivo],
            'Mejor Solucion (Z)': [Modelo_posiciones.objVal],
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
        print(f"  ⚠️ La instancia no encontró solución. Estado: {Modelo_posiciones.status}\n")
        tiempo_anterior = Modelo_posiciones.Runtime if hasattr(Modelo_posiciones, 'Runtime') else 0
    
    # --- Liberar memoria ---
    Modelo_posiciones.dispose()

print("\n🎉 ¡PROCESO TOTALMENTE FINALIZADO! Revisa tu archivo Excel.")