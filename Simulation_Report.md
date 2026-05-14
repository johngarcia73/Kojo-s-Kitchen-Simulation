## John García Muñoz C-312

## Problema 1: La cocina de Kojo

## 1. Principales ideas seguidas para la solución del problema

El problema planteado requiere evaluar el impacto de agregar un tercer empleado durante las horas pico en el porcentaje de clientes que esperan más de 5 minutos para ser atendidos. Para ello se desarrolló un modelo de simulación de eventos discretos que replica el comportamiento del sistema real bajo ciertas simplificaciones.

### Las ideas clave fueron:

Modelar las llegadas de clientes como un proceso de Poisson no homogéneo, con tasas constantes por segmentos. Esto permite generar tiempos de llegada realistas.

Tipos de clientes (sándwich o sushi) con igual probabilidad (50% cada uno) y tiempos de servicio uniformes: 3–5 min para sándwich y 5–8 min para sushi.

Disciplina de cola FIFO y servidores polivalentes (cualquier empleado puede preparar cualquier plato).

Métrica principal: porcentaje de clientes cuyo tiempo de espera (desde llegada hasta inicio del servicio) supera los 5 minutos.

Comparación de dos escenarios:

Actual: 2 empleados fijos durante toda la jornada (10:00–21:00).

Alternativo: 2 empleados fijos + 1 adicional durante los períodos pico (11:30–13:30 y 17:00–19:00).

Múltiples réplicas (100, 500, 1000 y 1500 en la ejecución reportada) para obtener estimaciones estadísticamente robustas (media y desviación estándar).

## 2. Modelo de Simulación de Eventos Discretos desarrollado

El modelo se implementó en Python utilizando un bucle de eventos gestionado mediante una cola de prioridad. A continuación se describen sus componentes esenciales:

### 2.1 Generación de llegadas

Se divide el día (660 minutos) en 5 intervalos con tasas constantes.

Para cada intervalo se genera un número aleatorio de llegadas según una distribución Poisson con media λ × duración.

Las llegadas se distribuyen uniformemente dentro del intervalo y se ordenan cronológicamente.

A cada llegada se le asigna un tipo (sándwich o sushi) con probabilidad 0.5.

### 2.2 Eventos considerados

arrival: ocurre en el tiempo de llegada de un cliente. Se intenta asignar un servidor libre; si no lo hay, el cliente ingresa a la cola FIFO.

departure: ocurre cuando un servidor termina su servicio. Se libera el servidor y se atiende al siguiente cliente en cola (si existe).

staff_change: solo en el escenario alternativo. Se programa la adición del tercer empleado al inicio de cada pico y su eliminación al finalizar. Si al eliminar el empleado está ocupado, se marca como inactivo y se retira al terminar su servicio actual.

stop: evento de fin de simulación a las 21:00.

### 2.3 Medición del tiempo de espera

El tiempo de espera se calcula como inicio_del_servicio - llegada. Se registra para cada cliente que es efectivamente atendido (todos lo son, pues no se considera abandono por hartazgo; el umbral solo mide porcentaje de espera > 5 min).

### 2.4 Manejo de servidores

Se utiliza un contador de servidores libres (free_servers) y una lista (service_end_times) que almacena los tiempos de finalización de los servicios activos. Los servidores son indistinguibles, por lo que no se modelan individualmente. Al iniciar un servicio, se reduce el contador y se agrega el tiempo de fin a un heap. Al ocurrir una salida (evento departure), se liberan todos los servicios cuyo tiempo de fin sea menor o igual al actual, incrementando el contador. La adición o eliminación de un empleado extra modifica el total de servidores (total_servers) y el contador de libres correspondientemente.

### 2.5 Réplicas y análisis estadístico

Se ejecutan réplicas independientes (cambiando la semilla aleatoria) para cada escenario. Se calcula la media y desviación estándar del porcentaje de espera > 5 min.

## 3. Resumen de los resultados

Se evaluaron tres combinaciones de tasas de llegada (normal, pico) con diferentes números de réplicas (100, 500, 1000 y 1500). La métrica es el **porcentaje de clientes que esperan más de 5 minutos** para ser atendidos, reportado como `media ± desviación estándar` entre réplicas.

### Tabla 1. Resultados completos por escenario

| Tasas (normal, pico) | Réplicas | Escenario actual (2 emp.) (%) | Escenario alternativo (3 emp. en picos) (%) | Reducción (pp) |
| -------------------- | -------- | ----------------------------- | ------------------------------------------- | -------------- |
| **0.2, 0.5**         | 100      | 66.50 ± 9.64                  | 21.33 ± 11.17                               | 45.17          |
|                      | 500      | 66.04 ± 9.92                  | 21.33 ± 11.90                               | 44.71          |
|                      | 1000     | 66.12 ± 10.33                 | 21.57 ± 12.29                               | 44.55          |
|                      | 1500     | 66.25 ± 10.26                 | 21.55 ± 12.16                               | 44.70          |
| **0.3, 0.5**         | 100      | 79.05 ± 12.55                 | 34.21 ± 14.70                               | 44.84          |
|                      | 500      | 77.93 ± 12.07                 | 33.00 ± 14.71                               | 44.93          |
|                      | 1000     | 78.27 ± 11.48                 | 33.02 ± 14.26                               | 45.25          |
|                      | 1500     | 78.53 ± 11.56                 | 33.30 ± 14.37                               | 45.23          |
| **0.3, 0.3**         | 100      | 32.16 ± 13.10                 | 18.34 ± 8.63                                | 13.82          |
|                      | 500      | 32.04 ± 12.60                 | 18.42 ± 8.61                                | 13.62          |
|                      | 1000     | 31.93 ± 12.81 (\*)            | 18.5 ± 8.8 (\*estimado)                     | ~13.4          |
|                      | 1500     | 31.87 ± 12.90                 | 18.52 ± 8.96                                | 13.35          |

---

## 2. Análisis de sensibilidad a las tasas de llegada

### 2.1 Efecto de aumentar la tasa normal (0.2 → 0.3) con pico fijo = 0.5

- **Escenario actual**: el porcentaje de clientes insatisfechos sube de ≈66% a ≈78% (+12 puntos porcentuales).  
  Una demanda normal más alta (de 12 a 18 clientes/hora) satura el sistema incluso fuera de los picos, generando colas persistentes.
- **Escenario alternativo**: también aumenta, de ≈21% a ≈33% (+12 puntos).  
  El tercer empleado sigue siendo muy efectivo, pero no logra contener el nivel extra de demanda.
- **Reducción absoluta** (actual – alternativo): se mantiene estable en ≈45 puntos, indicando que el beneficio del empleado extra es robusto ante incrementos en la tasa normal cuando el pico es alto.

### 2.2 Efecto de reducir la tasa pico (0.5 → 0.3) con normal fija = 0.3

- **Escenario actual**: el porcentaje cae drásticamente de ≈78% a ≈32% (–46 puntos).  
  Con tasas iguales (0.3 clientes/min ≈ 18 clientes/hora), la capacidad de dos empleados (~22.9 clientes/hora) es suficiente para atender la demanda sin grandes acumulaciones.
- **Escenario alternativo**: baja de ≈33% a ≈18% (–15 puntos). La mejora adicional por el tercer empleado es mucho menor (solo ≈13 puntos porcentuales).
- **Conclusión**: el tercer empleado es más valioso cuando la tasa pico supera significativamente la capacidad (pico ≥ 0.5). Si el pico es moderado (0.3), la ganancia en calidad es modesta y probablemente no justifica el potencial costo del empleado.

---

## 3. Convergencia con el número de réplicas

- **Medias**: se estabilizan muy rápido. Entre 100 y 1500 réplicas, la variación de la media es inferior a 1 punto porcentual en todas las combinaciones.
- **Desviaciones estándar**: prácticamente constantes (variación < 2 puntos).  
  Esto indica que 100 réplicas ya proporcionan una estimación fiable de la media y la desviación del sistema.
- **Conclusión**: futuras ejecuciones modificadas
  de la simulación pueden realizarse satisfactoriamente usando solo 100 réplicas.

---

## 4. Interpretación práctica para el administrador

### Estudiar el flujo de llegada de los clientes

| Situación de demanda                    | Con 2 empleados   | Con 3 empleados (solo picos) | Decisión recomendada                                      |
| --------------------------------------- | ----------------- | ---------------------------- | --------------------------------------------------------- |
| **Original:** normal 0.2, pico 0.5      | 66% espera >5 min | 22% espera >5 min            | **Contratar** – mejora muy grande                         |
| **Demanda normal alta:** 0.3, pico 0.5  | 78% espera >5 min | 33% espera >5 min            | **Contratar** – mejora aún necesaria, aunque persiste 33% |
| **Pico moderado:** 0.3 normal, 0.3 pico | 32% espera >5 min | 18% espera >5 min            | **No contratar** – mejora pequeña, costo no justificado   |

### Recomendación

Puesto que el escenario donde las tasas de llegada hora normal y hora pico son iguales es poco realista, a falta de cualquier otro dato y desconocidas estas catidades, lo mejor es contratar un empleado adicional para hora pico.

---

## 5. Limitaciones

- **Abandono de clientes**: en esta simulación todos los clientes esperan hasta ser atendidos.
- **Análisis económico**: no se miden costos de personal ni precios de los platos.
