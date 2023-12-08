import pandas as pd
import random
from datetime import datetime


# Especifica la ruta del archivo CSV
archivo_csv = 'orders.csv'

# Lee el archivo CSV en un DataFrame de pandas
data_frame1 = pd.read_csv(archivo_csv,delimiter=';', nrows=300)

# Especifica la ruta del archivo CSV
archivo_csv2 = 'couriers.csv'

# Lee el archivo CSV en un DataFrame de pandas
data_frame2 = pd.read_csv(archivo_csv2, delimiter=';',nrows=300)

import hashlib
def asignar_id(latitud, longitud):
    # Combina la latitud y longitud como una cadena
    cadena_coordenadas = f"{latitud},{longitud}"

    # Calcula el hash de la cadena combinada
    hash = hashlib.md5(cadena_coordenadas.encode()).hexdigest()
    id_asignado=hash[:4]
    return id_asignado

def asignar_id2(latitud, longitud):
    # Combina la latitud y longitud como una cadena
    cadena_coordenadas = f"{latitud},{longitud}"

    # Calcula el hash de la cadena combinada
    hash = hashlib.md5(cadena_coordenadas.encode()).hexdigest()
    id_asignado=hash[:3]
    return id_asignado


# Asigna IDs a las coordenadas en la base de datos
data_frame1['Establecimiento_id'] = data_frame1.apply(lambda row: asignar_id(row['pick_up_lat'], row['pick_up_lng']), axis=1)

# Asigna IDs a las coordenadas en la base de datos
data_frame1['Cliente_id'] = data_frame1.apply(lambda row: asignar_id2(row['drop_off_lat'], row['drop_off_lng']), axis=1)




# Datos 
data = {
    'Pedido': data_frame1['order_id'],
    'Establecimiento_ID': data_frame1['Establecimiento_id'],
    'Cliente_ID': data_frame1['Cliente_id'],
    'Latitud_Cliente': data_frame1['drop_off_lat'],
    'Longitud_Cliente': data_frame1['drop_off_lng'],
    'Latitud_Establecimiento': data_frame1['pick_up_lat'],
    'Longitud_Establecimiento': data_frame1['pick_up_lng']
}


df=pd.DataFrame(data)

data_domiciliarios = {
    'Domiciliario_ID': data_frame2['courier_id'],
    'Latitud_Actual': data_frame2['on_lat'],
    'Longitud_Actual': data_frame2['on_lng']
}

dfDomi=pd.DataFrame(data_domiciliarios)



# Datos para el algoritmo
couriers_df = dfDomi.set_index('Domiciliario_ID').to_dict(orient='index')
orders_df = df.set_index('Pedido').to_dict(orient='index')


import random

def calcular_distancia(lat1, lon1, lat2, lon2):
    # Función para calcular la distancia entre dos puntos usando la fórmula euclidiana
    distancia = ((lat1 - lat2)**2 + (lon1 - lon2)**2)**0.5
    return distancia

def grasp_constructive_phase(couriers, orders, alpha):
    # Fase constructiva del GRASP para asignar órdenes a mensajeros
    assigned_orders = {}
    couriers_available = couriers.copy()
    orders_pending = orders.copy()

    while orders_pending:
        # Calcula los valores "codiciosos" para cada combinación de mensajero y orden
        greedy_values = []
        for courier_id, courier in couriers_available.items():
            for order_id, order in orders_pending.items():
                distance = calcular_distancia(
                    courier['Latitud_Actual'], courier['Longitud_Actual'],
                    order['Latitud_Cliente'], order['Longitud_Cliente']
                )
                greedy_values.append((distance, courier_id, order_id))

        # Ordena los valores codiciosos y selecciona los mejores alpha porcentajes
        greedy_values.sort(key=lambda x: x[0])
        top_alpha = greedy_values[:max(1, int(alpha * len(greedy_values)))]
        selected_courier_id, selected_order_id = random.choice(top_alpha)[1:]

        # Asigna la orden seleccionada al mensajero
        if selected_courier_id not in assigned_orders:
            current_establishment = orders[selected_order_id]['Establecimiento_ID']
            assigned_orders[selected_courier_id] = [current_establishment]

        assigned_orders[selected_courier_id].append(selected_order_id)
        del orders_pending[selected_order_id]

    return assigned_orders

def busqueda_local(couriers, orders, assigned_orders):
    # Búsqueda local para mejorar la asignación de órdenes a mensajeros
    mejor_asignacion = assigned_orders.copy()
    mejor_distancia_total = sum([
        calcular_distancia(
            couriers[courier_id]['Latitud_Actual'],
            couriers[courier_id]['Longitud_Actual'],
            orders[order_id]['Latitud_Cliente'],
            orders[order_id]['Longitud_Cliente']
        )
        for courier_id, orders_list in assigned_orders.items() for order_id in orders_list[1:]
    ])

    for courier_id_1, orders_assigned_1 in assigned_orders.items():
        for courier_id_2, orders_assigned_2 in assigned_orders.items():
            if courier_id_1 != courier_id_2:
                for order_id_1 in orders_assigned_1[1:]:
                    for order_id_2 in orders_assigned_2[1:]:
                        nueva_asignacion = assigned_orders.copy()
                        if order_id_1 in nueva_asignacion[courier_id_1]:
                            nueva_asignacion[courier_id_1].remove(order_id_1)
                        if order_id_2 in nueva_asignacion[courier_id_2]:
                            nueva_asignacion[courier_id_2].remove(order_id_2)
                        nueva_asignacion[courier_id_1].append(order_id_2)
                        nueva_asignacion[courier_id_2].append(order_id_1)

                        # Lógica para calcular la nueva distancia total y actualizar mejor_asignacion si es mejor
                        nueva_distancia_total = sum([
                            calcular_distancia(
                                couriers[courier_id]['Latitud_Actual'],
                                couriers[courier_id]['Longitud_Actual'],
                                orders[order_id]['Latitud_Cliente'],
                                orders[order_id]['Longitud_Cliente']
                            )
                            for courier_id, orders_list in nueva_asignacion.items() for order_id in orders_list[1:]
                        ])

                        if nueva_distancia_total < mejor_distancia_total:
                            mejor_asignacion = nueva_asignacion
                            mejor_distancia_total = nueva_distancia_total

    return mejor_asignacion

def reactive_grasp(couriers, orders, alpha, iterations):
    # GRASP reactiva para encontrar la mejor solución en varias iteraciones
    best_solution = None
    best_cost = float('inf')

    for _ in range(iterations):
        solution = grasp_constructive_phase(couriers, orders, alpha)
        # Búsqueda Local basada en la Solución Constructiva
        solucion_local = busqueda_local(couriers, orders, solution)

        # Calcular el costo para la solución actual
        current_cost = sum([
            calcular_distancia(
                couriers[courier_id]['Latitud_Actual'],
                couriers[courier_id]['Longitud_Actual'],
                orders[order_id]['Latitud_Cliente'],
                orders[order_id]['Longitud_Cliente']
            )
            for courier_id, orders_list in solucion_local.items() for order_id in orders_list[1:]
        ])

        # Actualizar la mejor solución si la solución actual es mejor
        if current_cost < best_cost:
            best_solution = solucion_local
            best_cost = current_cost

    # Formatear la mejor solución para su presentación
    formatted_solution = [[] for _ in range(len(couriers))]
    for courier_id, route in best_solution.items():
        formatted_route = [route[0]]  # Primer elemento de la ruta es el establecimiento
        current_establishment = route[0]
        cliente_count = 0
        for order_id in route[1:]:
            if isinstance(order_id, str):  # Establecimiento
                current_establishment = order_id
                formatted_route.append(order_id)
                cliente_count = 0  # Reiniciar el contador de clientes al cambiar de establecimiento
            else:  # Cliente
                formatted_route.append(orders[order_id]['Cliente_ID'])
                cliente_count += 1
                if cliente_count == 3:  # Límite de 3 clientes por establecimiento
                    formatted_route.append(current_establishment)  # Volver al establecimiento
                    cliente_count = 0  # Reiniciar el contador de clientes
        formatted_solution[courier_id - 1] = formatted_route

    return formatted_solution


# Ejemplo de uso:
alpha_value = 0.1
iterations = 100

# Ejecutar el algoritmo GRASP con un solo valor de alpha
formatted_solution = reactive_grasp(couriers_df, orders_df, alpha_value, iterations)

# Imprimir resultados
print("\nSolución GRASP:")
for i, ruta_domiciliario in enumerate(formatted_solution):
    print(f"Domiciliario {i + 1}: {ruta_domiciliario}")



def calcular_distancia(lat1, lon1, lat2, lon2):
    # Función para calcular la distancia euclidiana entre dos puntos geográficos
    return ((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2) ** 0.5

def evaluar(df, dfDomi, sInicial):
    # Función para evaluar una solución de rutas de domiciliarios
    costoT = 0  # Costo total de las rutas
    tiempoT = 0  # Tiempo total de las rutas
    tiempos = [[] for _ in range(len(dfDomi))]  # Lista para almacenar tiempos por domiciliario

    for domiciliario_index, ruta in enumerate(sInicial):
        # Ignorar rutas vacías o con un solo nodo
        if not ruta or len(ruta) < 2:
            continue

        distanciaDomi = 0  # Distancia total recorrida por el domiciliario
        tiempoDomi = 0  # Tiempo total empleado por el domiciliario

        # Ubicación inicial del domiciliario
        lat_inicial = dfDomi.loc[domiciliario_index, 'Latitud_Actual']
        lon_inicial = dfDomi.loc[domiciliario_index, 'Longitud_Actual']

        for i in range(len(ruta) - 1):
            origen = ruta[i]
            destino = ruta[i + 1]

            # ORIGEN
            if i % 2 == 0:  # Establecimiento
                origenE = df[df['Establecimiento_ID'] == origen]
                if not origenE.empty:
                    lat_origen = origenE['Latitud_Establecimiento'].values[0]
                    lon_origen = origenE['Longitud_Establecimiento'].values[0]
                else:
                    continue
            else:  # Cliente
                origenC = df[df['Cliente_ID'] == origen]
                if not origenC.empty:
                    lat_origen = origenC['Latitud_Cliente'].values[0]
                    lon_origen = origenC['Longitud_Cliente'].values[0]
                else:
                    continue

            # Calcular la distancia entre la ubicación actual y el punto de origen
            distancia = calcular_distancia(lat_inicial, lon_inicial, lat_origen, lon_origen)

            # Actualizar distancias y tiempos
            distanciaDomi += distancia
            tiempoDomi += distancia * 2000  # 2 minutos por km

            # DESTINO
            if (i + 1) % 2 == 0:  # Establecimiento
                destinoE = df[df['Establecimiento_ID'] == destino]
                if not destinoE.empty:
                    lat_destino = destinoE['Latitud_Establecimiento'].values[0]
                    lon_destino = destinoE['Longitud_Establecimiento'].values[0]
                else:
                    continue
            else:  # Cliente
                destinoC = df[df['Cliente_ID'] == destino]
                if not destinoC.empty:
                    lat_destino = destinoC['Latitud_Cliente'].values[0]
                    lon_destino = destinoC['Longitud_Cliente'].values[0]
                else:
                    continue

            # Calcular la distancia entre el punto de origen y el punto de destino
            distancia = calcular_distancia(lat_origen, lon_origen, lat_destino, lon_destino)

            # Actualizar distancias y tiempos
            distanciaDomi += distancia
            tiempoDomi += distancia * 2000  # 2 minutos por km

        # Actualizar el tiempo total y el costo total
        tiempoT += tiempoDomi
        costoT += distanciaDomi * 1000000  # 1000COP por km
        tiempos[domiciliario_index] = tiempoDomi

    return costoT, tiempoT, tiempos

# Ejemplo de uso
costo, tiempo, tiempos = evaluar(df, dfDomi, formatted_solution)
print(f"Costo total: ${costo}")
print(f"Tiempo total: {tiempo} minutos")
