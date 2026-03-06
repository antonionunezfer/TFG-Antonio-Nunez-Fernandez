from gurobipy import GRB, Model, quicksum
import pandas as pd
import os

# --- Configuración de rutas ---
carpeta_instancias = '..\..\DATOS\FASE1'
archivo_excel = 'Resultados_Precedencias_Con_Peso.xlsx' # Nombre cambiado para no mezclar

# Obtener solo los archivos .txt de la carpeta
archivos_txt = [f for f in os.listdir(carpeta_instancias) if f.endswith('.txt')]
total_instancias = len(archivos_txt)

# Variable para guardar el tiempo de la instancia anterior
tiempo_anterior = None

print("\n" + "⭐"*30)
print(f"🚀 INICIANDO LOTE (MODELO CON PESOS): {total_instancias} instancias detectadas")
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
        print("⏱️  TIEMPO ANTERIOR  : N/A (Esta es la primera)")
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
        
    # Lectura de los pesos
    w = [int(k.strip()) for k in lineas[-trabajos:]]

    M = sum(p[i][j] for i in range(trabajos) for j in range(maquinas))

    # --- Configuración del Modelo ---
    Modelo_precedencias_CON_PESO = Model("Modelo_precedencias")
    Modelo_precedencias_CON_PESO.setParam(GRB.Param.TimeLimit, 3600)
    Modelo_precedencias_CON_PESO.setParam('OutputFlag', 0)  # Gurobi en modo silencioso

    # --- Variables de decisión ---
    α = Modelo_precedencias_CON_PESO.addVars(trabajos, trabajos, vtype=GRB.BINARY, name="alfa")
    C = Modelo_precedencias_CON_PESO.addVars(trabajos, maquinas, lb=0, vtype=GRB.CONTINUOUS, name="C")

    # --- Restricciones ---
    for i in range(trabajos):
        for k in range(i + 1, trabajos):
            Modelo_precedencias_CON_PESO.addConstr(α[i, k] + α[k, i] == 1, name=f"prec_{i}_{k}")

    for i in range(trabajos):
        Modelo_precedencias_CON_PESO.addConstr(
            C[i, 0] >= quicksum(p[k][0] * α[k, i] for k in range(trabajos) if k != i) + p[i][0],
            name=f"maquina_0_trabajo_{i}"
        )

    for i in range(trabajos):
        for k in range(trabajos):
            if i != k:
                for j in range(maquinas):
                    Modelo_precedencias_CON_PESO.addConstr(
                        C[k, j] >= C[i, j] + p[k][j] * α[i, k] - M * (1 - α[i, k]),
                        name=f"disyuntiva_{i}_{k}_{j}"
                    )
                
    for i in range(trabajos):
        for j in range(1, maquinas):
            Modelo_precedencias_CON_PESO.addConstr(
                C[i, j] >= C[i, j-1] + p[i][j], 
                name=f"secuencia_{i}_{j}"
            )

    # --- Función objetivo (CON PESOS) ---
    ultima_maquina = maquinas - 1
    Modelo_precedencias_CON_PESO.setObjective(
        quicksum(w[i] * C[i, ultima_maquina] for i in range(trabajos)), 
        GRB.MINIMIZE
    )

    # --- Resolver el modelo ---
    Modelo_precedencias_CON_PESO.optimize()

    # --- Exportación a Excel y actualización de tiempo ---
    if Modelo_precedencias_CON_PESO.status in [GRB.OPTIMAL, GRB.TIME_LIMIT]:
        # Guardamos el tiempo para mostrarlo en la SIGUIENTE iteración
        tiempo_anterior = Modelo_precedencias_CON_PESO.Runtime
        gap_actual = Modelo_precedencias_CON_PESO.MIPGap * 100
        
        nuevo_registro = pd.DataFrame({
            'Instancia': [nombre_archivo],
            'Mejor Solucion (Z)': [Modelo_precedencias_CON_PESO.objVal],
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
        print(f"  ⚠️ La instancia no encontró solución. Estado: {Modelo_precedencias_CON_PESO.status}\n")
        tiempo_anterior = Modelo_precedencias_CON_PESO.Runtime if hasattr(Modelo_precedencias_CON_PESO, 'Runtime') else 0
    
    # --- Liberar memoria ---
    Modelo_precedencias_CON_PESO.dispose()

print("\n🎉 ¡PROCESO TOTALMENTE FINALIZADO! Revisa tu archivo Excel.")