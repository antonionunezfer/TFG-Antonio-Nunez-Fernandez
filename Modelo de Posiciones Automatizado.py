from gurobipy import GRB, Model, quicksum
import pandas as pd
import os
import re
import time

# --- Configuracion de rutas ---
carpeta_instancias = '..\..\DATOS'
archivo_excel = 'Resultados_Posiciones.xlsx'

archivos_txt = [f for f in os.listdir(carpeta_instancias) if f.endswith('.txt')]

def orden_natural(texto):
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', texto)]

archivos_txt.sort(key=orden_natural)
total_instancias = len(archivos_txt)
tiempo_anterior = None

TIEMPO_LIMITE = 3600

def callback_tiempo(model, where):
    if where == GRB.Callback.MIPNODE or where == GRB.Callback.MIPSOL:
        tiempo_transcurrido = time.time() - model._inicio
        if tiempo_transcurrido >= TIEMPO_LIMITE:
            model.terminate()

print("\n" + "*"*30)
print(f"INICIANDO LOTE (MODELO POSICIONES): {total_instancias} instancias detectadas")
print("*"*30 + "\n")

for indice, nombre_archivo in enumerate(archivos_txt, start=1):
    ruta_archivo = os.path.join(carpeta_instancias, nombre_archivo)
    faltan = total_instancias - indice

    print("="*60)
    print(f"INSTANCIA ACTUAL : {nombre_archivo}")
    print(f"PROGRESO         : [ {indice} / {total_instancias} ] -> Faltan {faltan}")
    print(f"TIEMPO ANTERIOR  : {f'{tiempo_anterior:.2f} s' if tiempo_anterior is not None else 'N/A'}")
    print("="*60)

    with open(ruta_archivo) as f:
        lineas = f.readlines()

    trabajos, maquinas = map(int, lineas[0].split())
    p = []
    for i in range(1, trabajos + 1):
        valores = list(map(int, lineas[i].split()))
        tiempos = [valores[j + 1] for j in range(0, len(valores), 2)]
        p.append(tiempos)

    posiciones = trabajos

    Modelo_posiciones = Model("Modelo_posiciones")
    Modelo_posiciones.setParam(GRB.Param.TimeLimit, TIEMPO_LIMITE)
    Modelo_posiciones.setParam('OutputFlag', 0)

    beta = Modelo_posiciones.addVars(trabajos, posiciones, vtype=GRB.BINARY, name="beta")
    C = Modelo_posiciones.addVars(posiciones, maquinas, lb=0, vtype=GRB.CONTINUOUS, name="C")

    for i in range(trabajos):
        Modelo_posiciones.addConstr(quicksum(beta[i, k] for k in range(posiciones)) == 1)
    for k in range(posiciones):
        Modelo_posiciones.addConstr(quicksum(beta[i, k] for i in range(trabajos)) == 1)

    Modelo_posiciones.addConstr(C[0, 0] == quicksum(p[i][0] * beta[i, 0] for i in range(trabajos)))
    for k in range(1, posiciones):
        Modelo_posiciones.addConstr(C[k, 0] >= C[k-1, 0] + quicksum(p[i][0] * beta[i, k] for i in range(trabajos)))
    for k in range(posiciones):
        for j in range(1, maquinas):
            Modelo_posiciones.addConstr(C[k, j] >= C[k, j-1] + quicksum(p[i][j] * beta[i, k] for i in range(trabajos)))
    for k in range(1, posiciones):
        for j in range(1, maquinas):
            Modelo_posiciones.addConstr(C[k, j] >= C[k-1, j] + quicksum(p[i][j] * beta[i, k] for i in range(trabajos)))

    ultima_maquina = maquinas - 1
    Modelo_posiciones.setObjective(quicksum(C[k, ultima_maquina] for k in range(posiciones)), GRB.MINIMIZE)

    Modelo_posiciones._inicio = time.time()
    Modelo_posiciones.optimize(lambda model, where: callback_tiempo(model, where))

    tiempo_anterior = time.time() - Modelo_posiciones._inicio

    tiene_solucion = Modelo_posiciones.SolCount > 0

    if Modelo_posiciones.status in [GRB.OPTIMAL, GRB.TIME_LIMIT] and tiene_solucion:
        gap_actual = Modelo_posiciones.MIPGap * 100
        estado_texto = "OPTIMAL" if Modelo_posiciones.status == GRB.OPTIMAL else "TIME_LIMIT"
        nuevo_registro = pd.DataFrame({
            'Instancia': [nombre_archivo],
            'Mejor Solucion': [Modelo_posiciones.objVal],
            'Tiempo (segundos)': [tiempo_anterior],
            'GAP (%)': [gap_actual],
            'Estado': [estado_texto]
        })
        print(f"  Completado [{estado_texto}]. GAP: {gap_actual:.2f}% | Tiempo: {tiempo_anterior:.1f}s\n")
    elif Modelo_posiciones.status == GRB.TIME_LIMIT and not tiene_solucion:
        nuevo_registro = pd.DataFrame({
            'Instancia': [nombre_archivo],
            'Mejor Solucion': [None],
            'Tiempo (segundos)': [tiempo_anterior],
            'GAP (%)': [None],
            'Estado': ['TIME_LIMIT_NO_SOL']
        })
        print(f"  TIME_LIMIT sin solucion factible. Tiempo: {tiempo_anterior:.1f}s\n")
    else:
        nuevo_registro = pd.DataFrame({
            'Instancia': [nombre_archivo],
            'Mejor Solucion': [None],
            'Tiempo (segundos)': [tiempo_anterior],
            'GAP (%)': [None],
            'Estado': [f'ERROR_{Modelo_posiciones.status}']
        })
        print(f"  Estado inesperado: {Modelo_posiciones.status}\n")

    if os.path.exists(archivo_excel):
        df_existente = pd.read_excel(archivo_excel)
        df_final = pd.concat([df_existente, nuevo_registro], ignore_index=True)
    else:
        df_final = nuevo_registro
    df_final.to_excel(archivo_excel, index=False)

    Modelo_posiciones.dispose()

print("\nPROCESO TOTALMENTE FINALIZADO. Revisa tu archivo Excel.")
