# Lección «Suma de fracciones»: diseño pedagógico (borrador v1)

> Borrador para discutir con el equipo y revisar con la profesora. Lo marcado con **[DOCENTE]** necesita su opinión.
> Esta revisión no equivale a una certificación pedagógica.

## Objetivo

Al terminar, el alumno **suma fracciones con distinto denominador** y **puede explicar por qué** hay que buscar un denominador común: para que los pedazos sean del mismo tamaño. Además, lo aplica en un problema verbal que no ha visto antes.

## Ruta de habilidades (prerrequisitos)

| # | Habilidad | Ejemplo | Por qué va antes |
|---|---|---|---|
| 1 | Fracciones equivalentes | 2/3 = ?/12 | Sin esto no se puede convertir al denominador común |
| 2 | Suma con el mismo denominador | 2/7 + 3/7 | Fija la idea de que el denominador es el *tamaño del pedazo* y no se suma |
| 3 | Suma con distinto denominador | 1/2 + 1/3 | Objetivo de la lección |

Rango: denominadores del 2 al 12, fracciones propias y denominador común ≤ 36. **[DOCENTE]** ¿Es el rango adecuado para 1º de secundaria? ¿Incluimos números mixtos?

## Flujo de la sesión

1. **Diagnóstico**: un ejercicio por habilidad, sin pistas. «No lo sé todavía» es una respuesta válida y no se penaliza.
   - El alumno empieza en la **primera habilidad que falló**. Las anteriores se marcan como dominadas.
   - Si acierta las tres, pasa directo al reto final (recolocación hacia arriba).
2. **Explicación** corta: 3 ideas, un dibujo de barras y un «¿por qué funciona?».
3. **Práctica**: ejercicios generados por código y validados antes de mostrarse.
4. **Reto final (transferencia)**: un problema verbal (pizza, receta, distancia, agua) sin barras dibujadas y sin pistas hasta el primer error. Con 2 errores, el alumno regresa a practicar.
5. **Cierre**: resumen, errores superados y recomendación para la próxima sesión.
6. **Regreso tras ≥ 14 días**: primero un repaso rápido de lo ya dominado. Si falla, se hace un refuerzo puntual de esa habilidad antes de continuar.

## Criterio de dominio (provisional)

- **2 aciertos seguidos**, con **1 pista como máximo** en cada uno, y **al menos uno sin pistas**.
- Un acierto con 2 o más pistas no cuenta para la racha: «lo lograste con ayuda; hagamos otro sin pistas».
- Tras 6 ejercicios sin alcanzar el dominio, el sistema sugiere un descanso. No hay castigo.

**[DOCENTE]** ¿Le parecen suficientes 2 aciertos? ¿Deberíamos pedir que el alumno *explique* un paso, por ejemplo eligiendo entre opciones por qué se busca el denominador común?

## Pistas progresivas (ejemplo: 1/2 + 1/3)

| Nivel | Tipo | Texto |
|---|---|---|
| 1 | Pregunta conceptual | ¿Se pueden juntar directamente pedazos de tamaños distintos? |
| 2 | Estrategia | Busca un número que esté en la tabla del 2 y en la del 3. |
| 3 | Paso concreto | Un denominador común es 6. Convierte: 1/2 = ?/6 y 1/3 = ?/6. |
| 4 | Resolución acompañada | 1/2 = 3/6, 1/3 = 2/6 → 3/6 + 2/6 = 5/6 |

Las pistas 1 a 3 **nunca contienen el resultado**; hay una prueba automática que lo verifica. Si el alumno escribe «dame la respuesta», recibe la siguiente pista.

## Errores que detectamos y cómo respondemos

| Clave | Ejemplo con 1/2 + 1/3 | Respuesta del tutor (resumen) |
|---|---|---|
| `suma_num_y_den` | 2/5 | «Tiene lógica, pero 1/2 + 1/2 daría 2/4 = 1/2. ¡Dos mitades no pueden dar una mitad!» |
| `no_convirtio_numeradores` | 2/6 | «¡Bien el denominador común! Falta convertir los numeradores.» |
| `multiplico` | 1/6 | «Estamos juntando cantidades: sumamos, no multiplicamos.» |
| `invertida` | 6/5 | «Números correctos, pero volteados.» |
| `error_calculo` | 4/6 | «Procedimiento bien encaminado; revisa las cuentas.» |
| `solo_una_fraccion` | 1/2 | «Falta juntar la otra parte.» |
| `posible_dedo` | 5/7 | «¿Se te fue un dedo?» |
| `pensamiento_aditivo` | 2/3 = 11/12 | «Para que no cambie hay que *multiplicar* arriba y abajo, no sumar.» |
| `solo_factor` | 2/3 = 4/12 | «Encontraste el factor; ahora aplícalo al numerador.» |
| no interpretable | «3//4» | Se le pide reescribirla. **No cuenta como intento.** |

Una respuesta correcta sin simplificar (10/12) **cuenta como correcta**, con una nota opcional para simplificar. **[DOCENTE]** ¿Exigimos simplificar?

**[DOCENTE]** ¿Qué otros errores frecuentes ve en el salón que no estemos detectando?

## Casos de prueba (ya automatizados en `backend/tests/`)

- [x] `1/2 + 1/3 = 2/5` → retroalimentación específica
- [x] El alumno pide la respuesta directa → recibe una pista, no la respuesta
- [x] Alumno frustrado («me rindo») → empatía y descanso opcional
- [x] Errores de dedo → no se cuentan como intento fallido
- [x] Problemas generados inválidos (denominador 0, impropias, denominador común enorme) → se rechazan
- [x] Regreso después de 2 meses → repaso y refuerzo puntual
- [x] Comprensión independiente → reto verbal sin pistas iniciales
- [x] Borrar mis datos

Falta medir: calidad de las pistas con alumnos reales, costo por sesión con Claude y accesibilidad con lector de pantalla.

## Preguntas para la entrevista con la profesora

1. ¿Cuáles son los 3 errores más comunes al sumar fracciones en su experiencia?
2. ¿Cómo sabe que un alumno *entendió* y no solo memorizó el procedimiento?
3. ¿Le parecen bien el orden y el tono de nuestras 4 pistas?
4. ¿Qué criterio usaría para decir «ya puede avanzar»?
5. ¿Cómo responde usted cuando un alumno se frustra?
6. ¿Qué prerrequisito suele faltar y no se nota?
7. ¿Nos podría compartir un ejemplo de cómo explica este tema?
8. ¿Podría probar el prototipo y decirnos qué cambiaría?
