# Estándar de lección ThinkLoop

Cada curso es un archivo JSON en `backend/app/courses/content/` y lleva el número de orden en el nombre (`01-sumas.json`, `02-restas.json`…). El **contenido** (los textos) está separado de la **lógica**: los números, las respuestas y la detección de errores los calcula el código. Así una docente puede revisar y corregir los textos sin programar, y la IA nunca inventa ni califica.

## Estados de validación

| Estado (`metadatos.estado`) | Qué significa | Quién lo cambia |
|---|---|---|
| `borrador` | Lo redactó el equipo (con apoyo de IA). | — |
| `verificacion_matematica` | **Así están todos hoy (22 nov 2026).** Las cuentas se revisaron una por una, el grado se cotejó con la SEP y las pruebas automáticas pasan: cada ejercicio generado tiene la respuesta correcta según un cálculo independiente, ninguna pista revela el resultado y todos los errores detectables tienen su texto. | El equipo, al correr `pytest` |
| `revision_pedagogica` | Una docente revisó la claridad, el nivel, las pistas, las preguntas de comprobación y las sugerencias de clase. | Llenar `revisado_por` y `fecha_revision` |
| `publicada` | Se usa con alumnos y se mejora con lo que se observa. | El equipo |

La revisión de la profesora **no es una certificación oficial**. Sí es una revisión profesional valiosa, y así hay que presentarla en el pitch.

## Campos del curso

```jsonc
{
  "id": "MAT-SUMA",                 // código estable del curso
  "motor": "generico",              // "generico" (courses/generic.py) o "fracciones"
  "orden": 1,                       // posición en el catálogo (de básico a avanzado)
  "titulo": "Sumas",
  "nivel": "Primaria baja",
  "descripcion": "…",
  "portada": {"simbolo": "+", "tono": "naranja"},   // plantilla SVG propia, sin imágenes externas
  "prerrequisitos": [],             // ids de otros cursos
  "evaluacion": "…",                // cómo sabemos que lo aprendió (texto para el catálogo)
  "metadatos": {
    "fuente_curricular": "…",       // programa sintético de la SEP, grado y cita textual del contenido
    "referencias": ["…"],
    "licencia": "…",                // contenido original; licencia por definir
    "autor": "…",
    "revisado_por": null,
    "fecha_revision": null,
    "estado": "borrador"
  },
  "fundamentos": {                  // TEORÍA antes de practicar: qué es y por qué funciona
    "titulo": "…", "intro": "…",
    "tarjetas": [{"titulo": "…", "texto": "…", "visual": {"kind": "base10", "numero": 347}}],  // 4 a 6
    "pregunta": {"pregunta": "¿Por qué…?", "opciones": {…}, "correcta": "…", "retro": {…}},
    "fuentes": [{"titulo": "…", "url": "…", "cita": "fragmento breve", "uso": "para qué y con qué licencia"}]
  },
  "habilidades": [ … ],             // en orden de prerrequisito
  "reto_final": {"habilidad": "…", "historias": ["…{a}…{n1}…"]},   // problemas en contexto de la evaluación final
  "evaluacion_final": {"preguntas": [ {"pregunta": "¿Por qué…?", "opciones": {…}, "correcta": "…", "retro": {…}} ]}
}
```

## Evaluación final

Cada curso termina con una evaluación de **5 preguntas sin pistas ni IA** (`EXAM_SIZE` y `EXAM_PASS` en `lesson.py`):

1. un ejercicio de cada habilidad, de la más fácil a la más difícil (si el curso tiene pocas habilidades, se agregan ejercicios de las más avanzadas);
2. un problema en contexto, con una de las `historias` de `reto_final`;
3. una pregunta de «por qué», elegida al azar de `evaluacion_final.preguntas` (al menos 2 por curso, para que cambie si se vuelve a presentar).

Se aprueba con **4 de 5**. Al final, el alumno ve qué salió bien y, en lo que falló, su respuesta y la retroalimentación del error (`retro` del error o de la opción), **nunca la respuesta correcta**. Si no aprueba, se refuerzan solo las habilidades que falló y se vuelve a presentar. La constancia del curso exige aprobarla.

## Método Singapur (CPA)

Cada explicación tiene exactamente 3 ideas, en este orden:

```json
"ideas": [
  {"etapa": "concreto",  "texto": "Con objetos que se pueden tocar: bloques, fichas, una balanza…", "visual": {"kind": "base10", "numero": 23, "caption": "23 = 20 + 3"}},
  {"etapa": "pictorico", "texto": "Con un dibujo: el modelo de barras.", "visual": {"kind": "modelo", "filas": […]}},
  {"etapa": "abstracto", "texto": "Con números: la cuenta."}
]
```

La pantalla ya dice «Con objetos», «Con un dibujo» o «Con números»: el texto no lo repite. La etapa pictórica **siempre** lleva dibujo.

### Modelo de barras (`"kind": "modelo"`)

```json
{"kind": "modelo", "caption": "x + 5 = 12",
 "filas": [{"total": 12, "llave": "12",
            "segmentos": [{"resto": true, "texto": "x", "hueco": true},
                          {"n": 5, "texto": "5", "tono": "b"}]}]}
```

- Cada fila es una barra; `etiqueta` (opcional) va a su izquierda y `llave` debajo (cuánto vale la barra completa, o «?»).
- Cada segmento lleva su tamaño real `n`, o `resto: true` para «lo que falta para llegar a `total`». `repetir` dibuja grupos iguales; `hueco` lo dibuja punteado (lo que no se conoce); `tono` puede ser `a`, `b` o `warn`.
- Al navegador solo llegan proporciones aproximadas (veinteavos de la barra), nunca los tamaños exactos.

En cada habilidad, `visual_pista` es el modelo que acompaña a la primera pista, con las variables del ejercicio (`"{a}"`, `"{b}"`…). En `n`, `total` y `repetir` sí se pueden usar variables secretas (solo dan el tamaño aproximado); **en `texto`, `llave`, `etiqueta` y `caption` no**, y las pruebas lo comprueban.

Reglas de la teoría:
- de 4 a 6 tarjetas, una idea cada una;
- al menos una tarjeta explica **cómo saber que está bien** sin ayuda (comprobar con la operación inversa, estimar…);
- la pregunta final es de **por qué**, no de cómo;
- texto **propio**: las fuentes se citan, no se copian;
- dibujos disponibles: `base10`, `columnas`, `arreglo`, `reparto`, `cuadricula`, `balanza`, `modelo` (barras de Singapur) y `barras` (fracciones). Las pruebas comprueban también **las cuentas dentro de los dibujos**, en la teoría y en las explicaciones.

## Campos de cada habilidad

| Campo | Para qué |
|---|---|
| `id`, `nombre`, `objetivo` | Identificación y objetivo de aprendizaje. |
| `tipo` | Qué código genera y califica el ejercicio (ver la tabla de tipos). |
| `explicacion.ideas` | **3 ideas cortas**, una por pantalla: concreto, pictórico y abstracto (ver «Método Singapur»). |
| `visual_pista` | Modelo de barras de la primera pista, con los números del ejercicio. |
| `explicacion.por_que` | Por qué funciona; se muestra antes de la pregunta. |
| `comprobacion` | Pregunta con 3 opciones. Las incorrectas son errores típicos y **cada una trae su retroalimentación** (`retro`). |
| `otra_forma` | Explicación verificada con otra representación (dinero, cajas, balanza…). Es la base que adapta la IA en la ayuda extra. |
| `enunciado`, `ayuda_respuesta` | Texto del ejercicio con variables (`{a}`, `{b}`…) y cómo escribir la respuesta. |
| `pistas` | Pistas **progresivas**. Todas menos la última llevan un `paso` que el alumno debe responder para ver la siguiente. **Ninguna pista revela el resultado.** |
| `resolucion` | Resolución completa. **Solo se muestra como «ejemplo parecido» con OTROS números**, nunca para el ejercicio actual. Puede usar `{res}`. |
| `errores` | Errores de razonamiento que detecta el código. Cada uno tiene `retro` (para el alumno, sin avergonzar), `docente` (etiqueta del panel docente) y `accion` (qué hacer en clase). |

Formato de un paso:

```json
{"texto": "Empieza por las unidades: {u1} y {u2}.",
 "paso": {"campos": [{"etiqueta": "{u1} + {u2} =", "acepta": ["{us}"]}]}}
```

Un campo de opciones lleva `"opciones": ["Sí", "No"]` y `"acepta": ["No"]`.

## Tipos de ejercicio disponibles (`courses/generic.py`)

| Tipo | Ejercicio | Errores que detecta |
|---|---|---|
| `suma_basica` | 2 cifras sin llevar | sumar todos los dígitos |
| `suma_llevando` | 2 cifras llevando | olvidar llevar; escribir la columna completa (715) |
| `resta_basica` | 2 cifras sin pedir prestado | sumar en vez de restar |
| `resta_prestando` | 2 cifras pidiendo prestado | restar el menor del mayor; no descontar la decena prestada |
| `mult_tablas` | tablas (suma repetida) | sumar los factores; contar un grupo de más o de menos |
| `mult_una_cifra` | 2 cifras × 1 cifra | olvidar el valor de la decena; multiplicar solo unidades; pegar productos |
| `div_exacta` | reparto exacto | multiplicar; restar una sola vez |
| `div_residuo` | cociente y residuo (`7 r 2`) | residuo ≥ divisor; invertirlos; omitir el residuo |
| `cuadrado` | n² | n × 2; n + 2 |
| `raiz_exacta` | √ de un cuadrado perfecto | dividir entre 2 |
| `raiz_estimar` | √ entre dos enteros (`6 y 7`) | intervalo vecino; la mitad; un solo número |
| `alg_sustituir` | valor de ax + b | pegar coeficiente y valor (34); sumar en vez de multiplicar; olvidar un término |
| `alg_ec_suma` | x + a = b | sumar en vez de restar |
| `alg_ec_dos_pasos` | ax + b = c | dividir antes de restar; sumar b; restar a; no dividir |

Agregar un curso con estos tipos solo requiere un JSON nuevo (con sus etapas CPA y al menos 2 preguntas de `evaluacion_final`). Un tipo nuevo requiere programar su generador, su respuesta y la detección de errores en `generic.py`, y agregar su cálculo independiente en `tests/test_courses.py`.

## Lo que se verifica automáticamente (`tests/test_courses.py`)

- Cada ejercicio generado (cientos por tipo) tiene la respuesta correcta según un cálculo independiente y es del nivel esperado (divisiones exactas, raíces exactas, resultados no negativos).
- Todas las pistas menos la última traen paso. Cada distractor de la pregunta de comprobación tiene retroalimentación. Cada error detectable tiene texto para el alumno y para el docente.
- **Ninguna pista, enunciado, reto ni retroalimentación usa las variables que contienen la respuesta.**
- Todas las plantillas se llenan sin variables sin resolver.

## Lo que NO se puede verificar automáticamente

Si una explicación es clara, si el nivel es adecuado para la edad, si los errores frecuentes son los que de verdad aparecen en el salón y si las sugerencias de clase son útiles. Eso lo tiene que revisar una docente.
