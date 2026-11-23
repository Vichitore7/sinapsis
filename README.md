# ThinkLoop (nombre provisional)

Plataforma educativa con IA que **enseña a pensar**, no solo a dar respuestas.
MVP para UniconHub Hack / Claude Build Day (28 nov 2026): **7 cursos de matemáticas**, de lo más básico a lo más avanzado (sumas, restas, multiplicación, división, fracciones, álgebra inicial, potencias y raíces), alineados con el Plan de Estudio 2022 de la SEP. La lección de **fracciones** es la más completa: tiene barras pictóricas y predicción.

## El problema (para el pitch)

- Muchos alumnos en México pasan de grado arrastrando vacíos en matemáticas básicas. En PISA 2022, solo alrededor de un tercio de los jóvenes de 15 años alcanzó el nivel mínimo en matemáticas, frente a cerca de dos tercios en el promedio de la OCDE.
- Los alumnos **ya usan** chatbots de IA para la tarea. Como la IA entrega el resultado en segundos, se ve una tarea perfecta sin que haya aprendizaje: *hacer la tarea con IA no es lo mismo que aprender a resolverla* (advertencia de la OCDE).
- Un docente con 40 o más alumnos no alcanza a ver **qué** entiende cada uno.

> ⚠️ Antes del pitch, verifiquen cada cifra con su fuente original (informe PISA, INEGI, OCDE). Usen pocos datos y todos con fuente; eviten cifras de divulgación sin respaldo (por ejemplo «dopamina cada 15 segundos»).

## La solución en una frase

Un tutor socrático que **guía con preguntas y dibujos en vez de dar la respuesta**. Detecta el error de razonamiento exacto (por ejemplo `1/2 + 1/3 = 2/5`), lo hace visible con barras y le entrega al docente un **reporte de un minuto** con los errores de todo el grupo.

Bases pedagógicas que usamos:
- **Método CPA de Singapur (Concreto → Pictórico → Abstracto)**: cada explicación va de los objetos (bloques, fichas, balanza) al **modelo de barras** y al final a los números. La primera pista de la práctica dibuja el modelo de barras del ejercicio con «?» en lo que se busca.
- **Andamiaje que se retira**: pistas progresivas en la práctica y ninguna en la evaluación final.
- **Práctica de recuperación** (Roediger y Karpicke, 2006): al regresar tras ≥14 días, se comprueba con ejercicios distintos qué se conservó.
- **Autoexplicación y predicción**: comprobar la idea antes de practicar y estimar antes de calcular obliga a leer y pensar, no solo a tantear.
- **El error como información, no como castigo**: no hay vidas ni penalizaciones. La mascota se pone curiosa, no triste.

## Qué hace el MVP

0. **Cuenta simple y cuidadosa con menores**: el alumno entra con un **apodo y una contraseña**, sin correo, teléfono ni nombre real. Al registrarse recibe un **código de recuperación** que se muestra una sola vez; es la única forma de recuperar la cuenta, porque no hay correo. Las contraseñas se guardan con scrypt y los tokens solo como hash. Tras 5 intentos fallidos el usuario se bloquea unos minutos. Cada alumno solo ve sus propias sesiones.
1. **Catálogo de cursos** (`#/cursos`): portadas hechas con una plantilla SVG propia (sin imágenes con derechos de autor), nivel, avance y estado («Nuevo», «En curso», «Completado»). Cada curso muestra el estado de su contenido: hoy todos están en **verificación matemática** (falta la revisión docente).
2. **Teoría primero (fundamentos)**: al empezar un curso, el alumno lee de 4 a 6 tarjetas cortas sobre **qué es y por qué funciona**, con dibujos (bloques de base 10, columnas, arreglos de puntos, reparto, cuadrícula, balanza, barras de fracciones). Por ejemplo: qué es un número, cómo se agrupa en unidades, decenas y centenas, y por qué «llevamos». Termina con una pregunta de **por qué**, no de cómo, y una tarjeta de «así sabes que está bien» para comprobar sin ayuda. Cada tarjeta cita sus fuentes. Se puede releer en cualquier momento con el botón «📖 Teoría del curso».
3. **Diagnóstico**: una pregunta por habilidad del curso para ubicar al alumno. Puede decir «No lo sé todavía».
4. **Explicación** en 3 ideas cortas, una por pantalla, siguiendo el método Singapur: **con objetos → con un dibujo (modelo de barras) → con números**, cada etapa con su dibujo. Para avanzar no hay botón de «Entendido»: hay una **pregunta de comprobación** cuyas opciones incorrectas son errores típicos (por ejemplo «Sí se puede: da 2/5»), cada una con su retroalimentación.
5. **Práctica** con ejercicios generados *y validados por código*, con **pistas progresivas que se responden**. Todas las pistas, menos la última, traen un mini paso con casilla (por ejemplo «6 × ? = 24» o «¿Se pueden juntar directamente? Sí / No»). La siguiente pista se desbloquea solo al resolver ese paso. Así ya no se puede dar clic a todas las pistas sin leer. **La respuesta final nunca se muestra**: el último paso siempre lo da el alumno.
   - **Ayuda extra (botón «?»)**: se activa solo cuando ya se usaron todas las pistas y la respuesta sigue mal, o cuando un paso se falla 2 veces. Entonces el alumno puede:
     - **preguntarle a Loop (IA)** con sus palabras. La IA recibe la explicación verificada «de otra forma» del curso, las pistas que ya vio y sus intentos fallidos, y debe explicar distinto sin dar el resultado. Si aun así lo revela, el backend lo detecta y lo reemplaza por contenido verificado;
     - ver un **ejemplo parecido resuelto, con otros números**;
     - **probar con otro ejercicio** sin penalización.

     Mientras lee una explicación, el alumno también puede preguntarle a Loop.
   - **Predicción antes de calcular** (curso de fracciones): en la suma con distinto denominador, un ejercicio sí y otro no, el alumno estima primero «¿será mayor o menor que X?» (X cambia: la fracción mayor, 1 o 1/2). Si luego responde 2/5 tras haber predicho bien, Loop le señala que su estimación ya lo avisaba.
   - **Respuestas al azar**: con 2 respuestas incorrectas muy rápidas (menos de 5 segundos), Loop le pide ir con calma, sin castigo. Un acierto que llega después de 2 o más intentos fallidos no cuenta para el dominio.
6. **Detección de errores de razonamiento**, por ejemplo `1/2 + 1/3 = 2/5`, con una retroalimentación que no avergüenza.
7. **Dominio**: 2 aciertos seguidos con 1 pista como máximo cada uno, y al menos uno sin pistas. Se mide así, no por cantidad de ejercicios.
8. **Evaluación final de cada curso**: 5 preguntas sin pistas ni IA: un ejercicio de cada habilidad (más ejercicios de las más avanzadas si el curso tiene pocas), un problema en contexto (pizza, dinero, camiones, terrenos…) y una pregunta de «por qué». Se aprueba con **4 de 5**. Al final se muestra qué salió bien y qué revisar en cada pregunta, **nunca la respuesta correcta**. Si no se aprueba, se refuerzan solo las habilidades falladas y se vuelve a presentar. Si pasan 14 días a mitad de la evaluación, no se interrumpe con el repaso.
9. **Pausa y regreso**: guarda el punto exacto de la sesión. Si el alumno vuelve tras ≥14 días, empieza con un **repaso** de lo que ya dominaba; si falló algo, hace un refuerzo puntual.
10. **Empatía**: detecta frustración y ofrece un descanso aunque el chat esté bloqueado. Si el alumno pide la respuesta directa, Loop le propone otra forma de verlo.
11. **IA con memoria estructurada**: se le manda el contexto relevante, no el historial completo, para ahorrar tokens. Solo se usa en la explicación y en la ayuda extra.
12. **Progreso** (`#/progreso`): avance por curso, habilidades dominadas y errores que se dejaron atrás.
13. **Logros** (`#/logros`): premian **cómo se piensa, no cuánto se hace**. No hay logros como «resuelve 10 ejercicios». Hay 9:
    - corregir tu propio error sin pedir pista (*Detective de errores*);
    - estimar bien antes de calcular;
    - resolver paso a paso;
    - dejar atrás un error de razonamiento;
    - usar la ayuda extra y luego resolver;
    - aprobar una evaluación final;
    - recordar en un repaso;
    - tomar un descanso y regresar;
    - animarse a responder.
14. **Reconocimientos** (`#/reconocimientos`): una **constancia interna por curso**, cuando se dominan sus habilidades **y se aprueba la evaluación final** (muestra la calificación), imprimible o guardable en PDF. Dice claramente **«sin valor curricular»**.
15. **Barras pictóricas (CPA)** en las pistas y en la retroalimentación. En todos los cursos, la primera pista dibuja el **modelo de barras** con los números del ejercicio (en raíces, la cuadrícula del número de prueba); al navegador solo llegan proporciones aproximadas, nunca los tamaños exactos. Ejemplo: si el alumno responde `2/5`, ve que su resultado es *más pequeño* que `1/2` y se le pregunta «¿al juntar dos cantidades puede quedar menos que una de ellas?». En los problemas verbales no hay dibujos hasta la resolución acompañada, porque el alumno debe modelar el problema por su cuenta.
16. **Loop, la mascota guía**: cambia de ánimo según lo que pasa (piensa, celebra, anima tras un error, descansa). No tiene economía de premios, vidas ni castigos por inactividad.
17. **Panel docente** (`/#docente`, PIN en `.env`): el alumno escribe un **código de grupo** opcional al registrarse. El docente elige un **curso** y ve:
    - un titular de un minuto («El 45% del grupo suma numeradores y denominadores…»);
    - los errores de razonamiento ordenados por % de alumnos, con una sugerencia de **qué hacer en clase**;
    - el dominio por habilidad;
    - los alumnos que conviene acompañar (frustración, dependencia de pistas, muchos intentos fallidos);
    - el detalle por alumno.

    Todo se calcula con SQL, sin IA ($0). En modo demo, «Cargar grupo de ejemplo» crea 20 alumnos **simulados**, marcados como tales en pantalla.

**Principio de diseño:** la IA **nunca califica**. Las respuestas las revisa código determinista con pruebas (`fractions_engine.py` y `courses/generic.py`). La IA solo conversa. Así se reduce el costo y no hay correcciones alucinadas.

**Biblioteca curricular estructurada:** cada curso es un archivo `backend/app/courses/content/*.json` que sigue el [estándar de lección](docs/estandar-de-leccion.md). Ahí están el objetivo, los prerrequisitos, las ideas, la pregunta de comprobación, las pistas con sus pasos, los errores frecuentes, el reto y los metadatos (fuente, licencia, autor, estado de validación). Una docente puede revisar los textos sin tocar código. Para agregar un curso basta con un JSON nuevo si usa los tipos de ejercicio existentes.

## Fuentes y licencias

| Fuente | Cómo la usamos | ¿Se puede usar? |
|---|---|---|
| Programas sintéticos de la SEP (Plan de Estudio 2022, publicados en 2024) | Para alinear cada curso con su grado y fundamentar qué se enseña. Citamos **fragmentos breves** con la fuente. | Su aviso legal autoriza reproducirlos **solo sin fines comerciales, sin modificarlos y reconociendo la autoría**. Citar fragmentos como referencia está bien; **no** copiamos ni adaptamos su texto. Si ThinkLoop cobra a escuelas, conviene seguir así: citar, no reproducir. |
| OpenStax, *Prealgebra 2e* (Rice University) | Solo como **lectura complementaria** para la docente. | Licencia **CC BY-NC-SA 4.0** (no comercial) y **prohíbe usarlo en productos de IA generativa** sin permiso. Por eso no copiamos su texto ni se lo damos a la IA. |
| Textos de ThinkLoop (teoría, explicaciones, pistas) | Son **propios**. Los hechos matemáticos (valor posicional, propiedades de las operaciones) no tienen dueño; la redacción sí, y es nuestra. | Licencia por decidir (propuesta: CC BY-SA 4.0). |

No usamos Khan Academy ni libros de texto con derechos reservados como fuente de texto.

## Pantallas

| Ruta | Qué es |
|---|---|
| (sin sesión) | Entrar · Crear cuenta (apodo + contraseña) · Recuperar con código |
| `#/cursos` | Catálogo de cursos con portada, nivel y avance |
| `#/curso/MAT-SUMA` | Lección: temario a la izquierda; conversación, ejercicio y botón «?» a la derecha |
| `#/progreso` | Avance por curso |
| `#/logros` | Logros de razonamiento |
| `#/reconocimientos` | Constancias internas; `#/constancia/MAT-SUMA` es la versión imprimible |
| `#docente` | Panel docente |

En celular, el menú lateral pasa a ser una barra inferior y la lección muestra primero el ejercicio.

**Diseño:**
- naranja y blanco, con tipografía **Nunito** empaquetada en la app, sin peticiones a Google;
- bordes **redondos** en lo que se toca (tarjetas, botones, burbujas) y **rectos** en lo que es dato o documento (campos, tablas, constancias);
- modo oscuro automático.

## Estructura

```
backend/
  app/
    courses/
      content/*.json     # LA BIBLIOTECA: un JSON por curso (estándar de lección), para revisión docente
      generic.py         # motor de sumas, restas, multiplicación, división, raíces y álgebra
      fractions_course.py# adapta el motor de fracciones a la interfaz común
      base.py            # interfaz Course + detector de «la IA reveló la respuesta»
    fractions_engine.py  # fracciones: parseo, generación+validación, errores, pistas, barras
    lesson.py            # textos de fracciones, criterios de dominio, estilos del tutor
    tutor.py             # flujo para cualquier curso: diagnóstico → explicación → práctica → evaluación final → cierre / repaso
    auth.py              # cuentas sin correo: scrypt, tokens, código de recuperación, freno a intentos
    achievements.py      # logros de razonamiento y constancias internas
    teacher.py           # panel docente: errores agrupados por curso, sugerencias de clase, grupo demo simulado
    db.py                # SQLite: alumnos, tokens, sesiones, intentos, dominio, eventos, uso de IA
    ai/                  # proveedor intercambiable: mock ($0) | claude
    main.py              # API FastAPI
  tests/                 # 182 pruebas (contenido de cursos, motores, flujo, cuentas, ayuda extra, logros, panel docente)
frontend/                # React + Vite, sin librerías de UI (ligero)
  src/components/AuthScreen.jsx        # entrar / crear cuenta / recuperar
  src/components/CoursesPage.jsx       # catálogo de cursos (+ CourseCover.jsx: portadas SVG)
  src/components/LessonPage.jsx        # lección con temario, pasos, «?» y ayuda extra
  src/components/ProgressPage.jsx · AchievementsPage.jsx · CertificatesPage.jsx
  src/components/Mascot.jsx            # Loop, la mascota (SVG, sin imágenes externas)
  src/components/FractionVisual.jsx    # barras de fracciones (CPA)
  src/components/TeacherDashboard.jsx  # panel docente (#docente)
docs/estandar-de-leccion.md # formato de cada curso y proceso de validación
docs/leccion-fracciones.md  # diseño pedagógico para discutir con el equipo y la profesora
```

## Cómo correrlo

Requisitos: Python 3.12 y Node 20. En Ubuntu, si `python3 -m venv` falla, usa [uv](https://docs.astral.sh/uv/) o instala `python3.12-venv`.

```bash
# Backend (terminal 1)
cd backend
uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt
#   (alternativa: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt)
cp .env.example .env
.venv/bin/uvicorn app.main:app --reload --env-file .env
#   API en http://localhost:8000  ·  docs interactivas en http://localhost:8000/docs

# Frontend (terminal 2)
cd frontend
npm install
npm run dev
#   abre http://localhost:5173  ·  panel docente: http://localhost:5173/#docente (PIN demo: 1234)
```

Pruebas: `cd backend && .venv/bin/python -m pytest -q`

### Usar Claude en vez del modo demo

En `backend/.env`:

```
THINKLOOP_AI_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-...
THINKLOOP_AI_MODEL=claude-opus-5-5     # para gastar menos en pruebas: claude-haiku-5-5
```

La IA solo se llama cuando el alumno le pregunta algo a Loop: durante una explicación o en la ayuda extra, después de agotar las pistas. Por eso el costo por sesión es bajo. Puedes consultarlo en `GET /api/metrics/usage`. Con los modelos que lo admiten se activan los *fallbacks* del lado del servidor: si un filtro de seguridad rechaza una petición, se reintenta con otro modelo.

Para agregar otro proveedor (DeepSeek, Gemini…), crea `backend/app/ai/<nombre>_provider.py`, implementa `AIProvider.reply` y regístralo en `ai/__init__.py`.

### Demo del regreso tras dos meses

Con `THINKLOOP_DEMO=1` aparece «Demo: simular regreso» al pausar o al terminar. Ese botón simula 60 días de ausencia. Con `THINKLOOP_DEMO=0`, el backend ignora la simulación.

## API (resumen)

| Método | Ruta | Para qué |
|---|---|---|
| POST | `/api/auth/register` | `{username, password, tutor_style, group_code?}` → token + código de recuperación |
| POST | `/api/auth/login` | `{username, password}` → token |
| POST | `/api/auth/reset` | `{username, recovery_code, new_password}` → token + código nuevo |
| POST | `/api/auth/logout` | invalida el token |
| GET / PATCH / DELETE | `/api/me` | mis datos · cambiar estilo de tutor · borrar todo |
| GET | `/api/me/progress` · `/api/me/achievements` · `/api/me/certificates` | progreso por curso, logros, constancias |
| GET | `/api/courses` | catálogo con mi avance |
| POST | `/api/courses/{id}/session` | iniciar o reanudar un curso (`{days_away}` solo en demo) |
| POST | `/api/sessions/{sid}/answer` | `{answer}` o `{dont_know: true}` |
| POST | `/api/sessions/{sid}/hint` | siguiente pista |
| POST | `/api/sessions/{sid}/check` | `{option}` pregunta de comprobación de la explicación |
| POST | `/api/sessions/{sid}/exam` | `{option}` pregunta de «por qué» de la evaluación final |
| POST | `/api/sessions/{sid}/predict` | `{choice: "mayor"\|"menor"}` predicción antes de calcular |
| POST | `/api/sessions/{sid}/step` | `{values: [...]}` responder el mini paso de la pista |
| POST | `/api/sessions/{sid}/message` | pregunta a Loop (en la explicación o en la ayuda extra) |
| POST | `/api/sessions/{sid}/example` | ayuda extra: ejemplo parecido con otros números |
| POST | `/api/sessions/{sid}/skip` | ayuda extra: otro ejercicio, sin penalización |
| POST | `/api/sessions/{sid}/pause` | pausar guardando el punto exacto |
| GET | `/api/metrics/usage` | llamadas y tokens de IA |
| GET | `/api/teacher/groups` | grupos existentes (encabezado `X-Teacher-Pin`) |
| GET | `/api/teacher/groups/{código}?course=MAT-FRAC` | reporte del grupo en un curso: titular, errores, dominio, alumnos a acompañar |
| POST | `/api/teacher/demo-group` | solo demo: crea el grupo simulado `DEMO-1A` |

Las rutas del alumno exigen `Authorization: Bearer <token>` y solo dan acceso a lo propio. Los mensajes del tutor pueden traer `visual` (barras) además de `text`.

Todas las acciones de sesión devuelven la misma «vista»: fase, mensajes, ejercicio, pistas, acciones permitidas y progreso. El frontend solo pinta esa vista.

## Pendiente para el hackathon

- **Revisión docente del contenido**: el contenido lo redactó el equipo con apoyo de IA. Ya se verificó la parte matemática (cuentas, pasos, que ninguna pista revele el resultado) y el grado de cada curso contra los programas sintéticos de la SEP (2024). La cita está en `metadatos.fuente_curricular` de cada curso. **Falta la revisión pedagógica**: claridad, nivel de lenguaje, errores típicos reales del salón y sugerencias de clase (`courses/content/`, `lesson.py`, `teacher.py`). Al terminarla, se llenan `revisado_por` y `fecha_revision` y el estado pasa a `revision_pedagogica`. Ver [el estándar](docs/estandar-de-leccion.md).
- Verificar las cifras del pitch con su fuente.
- El docente entra con un PIN compartido; falta una cuenta docente real. También falta definir el consentimiento de madres, padres o tutores para menores.

## Funciones para más adelante (fuera del MVP, a propósito)

Las dejamos fuera para no sobreconstruir en una semana. Se pueden mencionar en el pitch como «siguiente fase».

| Función | Por qué esperar |
|---|---|
| **Escáner de cuaderno** (foto del procedimiento → el sistema ubica el paso del error) | Es lo más vistoso, pero leer matemáticas escritas a mano falla seguido, cuesta más por llamada (visión) y requiere cuidar la privacidad de fotos de menores. Primer paso posible: una demo controlada con fotos ya probadas. |
| **Modo sin conexión (offline-first / PWA)** | Sin internet no hay IA. Habría que definir qué funciona offline (el motor de fracciones y las pistas ya son deterministas, así que es viable) y cómo se sincroniza. |
| **WhatsApp como canal** | Choca con la prohibición de celulares en escuelas (nov 2026) y requiere la API de WhatsApp Business. |
| **Modo Aula** (retos en vivo para todo el salón) | Hay que definirlo bien primero. El panel docente ya es la base. |
| **Recompensas para la mascota** (comida, accesorios) | Es motivación externa. Solo se haría si no compite con el propósito de aprender. |
| Ejercicios generados por IA | Ya existen validadores (`validate_exercise` y las pruebas de contenido). Habría que verificar cada ejercicio con código (por ejemplo SymPy) antes de mostrarlo. |
| **Confirmación por correo** | Implica guardar correos de menores y depender de un servicio de envío. Por ahora basta el código de recuperación. |
| **Presupuesto diario de IA por alumno** (modos 1, 2 y 3 del documento de acceso gratuito) | La base ya existe: la IA solo actúa en la ayuda extra y `ai_usage` registra los tokens. Falta medir sesiones reales antes de fijar un límite. |
| Que el alumno dibuje su propio modelo de barras | Hoy el modelo lo dibuja Loop en la explicación y en la primera pista. En los problemas con texto, el siguiente paso sería que el alumno elija o arme el modelo antes de calcular. |
| Tutor por voz, más cursos (restar fracciones, porcentajes, ecuaciones con negativos…) | Siguiente paso después de validar los actuales con la profesora. |

- Licencia de código abierto (por decidir).
