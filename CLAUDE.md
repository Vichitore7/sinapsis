# Sinapsis (ThinkLoop) — contexto para Claude

Tutor de matemáticas con IA que **enseña a pensar, no a dar respuestas**. Proyecto de un equipo de 5 personas para **UniconHub Hack / Claude Build Day, 28 nov 2026**: Victor, Gera, Zulu, Samuel y Katia. «ThinkLoop» es el nombre provisional del producto; el repositorio se llama **sinapsis**. El equipo habla español: responde y escribe documentación en español de México.

Repositorio: https://github.com/Vichitore7/sinapsis (público)

## Estado actual (22 nov 2026)

Ya funciona de punta a punta:
- **7 cursos**, de lo básico a lo avanzado: Sumas → Restas → Multiplicación → División → Fracciones → Álgebra inicial → Potencias y raíces.
- **Flujo de cada curso**: teoría (fundamentos) → diagnóstico → explicación con pregunta de comprobación → práctica con pistas → **evaluación final** → cierre. Si el alumno regresa después de 14 días o más, empieza con un repaso (salvo a mitad de la evaluación).
- **Método Singapur (CPA)**: cada explicación tiene 3 etapas: con objetos → con un dibujo (modelo de barras) → con números. La primera pista de la práctica dibuja el modelo de barras del ejercicio con «?» en lo que se busca.
- **Evaluación final**: 5 preguntas sin pistas ni IA (un ejercicio por habilidad, un problema en contexto y una pregunta de «por qué»). Se aprueba con 4 de 5. Si no, se refuerzan solo las habilidades falladas y se vuelve a presentar. Al final se muestra qué salió bien y qué revisar, nunca la respuesta.
- **Pistas progresivas**: para ver la siguiente hay que responder el mini paso de la actual, y **la respuesta final nunca se muestra**.
- **Ayuda extra (botón «?»)**: se activa solo cuando ya se usaron todas las pistas o un paso se falló 2 veces. Ofrece preguntarle a Loop (IA), ver un ejemplo con otros números o cambiar de ejercicio.
- **Cuentas sin correo**: apodo y contraseña, más un código de recuperación que se muestra una vez.
- **Logros** que premian razonamiento, no cantidad, y **constancias por curso** «sin valor curricular», que exigen aprobar la evaluación final.
- **Panel docente** en `#docente` (PIN 1234 en la demo), con reporte por curso.
- **Diseño**: naranja y blanco con tipografía Nunito. Menú lateral, que se oculta dentro de una lección, y avatar arriba a la derecha.
- **182 pruebas** que pasan.

El contenido está en estado **«verificación matemática»**: las cuentas se revisaron y el grado de cada curso se cotejó con los programas sintéticos de la SEP. **Falta la revisión pedagógica de la profesora.** Todo lo redactó el equipo con apoyo de IA.

## Pendientes

- [ ] **Correcciones que Victor encontró al probar** («algunas cositas que no me gustaron»). Todavía no las ha dicho: preguntar al retomar.
- [ ] Agregar a Gera, Zulu, Samuel y Katia como colaboradores en GitHub. Victor lo iba a hacer; hacen falta para aprobar los pull requests a `main`.
- [ ] Revisión pedagógica de la profesora de secundaria y preparatoria: teoría, explicaciones (etapas CPA), pistas, modelos de barras, preguntas de la evaluación final, errores típicos y sugerencias del panel docente. Al terminar, llenar `revisado_por` y `fecha_revision` y cambiar `estado` a `revision_pedagogica` en cada JSON.
- [ ] Decidir si los segmentos desconocidos del modelo de barras de las pistas se dibujan a escala (hoy sí, aproximados a 1/20): si la x mide igual que un número conocido, se nota en el dibujo.
- [ ] Siguiente paso de Singapur: que el alumno elija o arme el modelo de barras de los problemas con texto antes de calcular.
- [ ] Decidir el modelo de IA. Propuesta del equipo: Claude Haiku 5.5 por defecto. Hoy `.env` usa `mock`, y `claude-opus-5-5` si se cambia a `claude`.
- [ ] Presupuesto diario de IA por alumno (los modos 1, 2 y 3 del documento de acceso gratuito). Primero hay que medir el consumo real con `ai_usage`.
- [ ] Cuenta docente real (hoy es un PIN compartido) y consentimiento de madres, padres o tutores para menores.
- [ ] Verificar con su fuente las cifras del pitch (PISA y demás).
- [ ] Los alumnos «Juan» y «Juan2» de la base de datos local se crearon antes del inicio de sesión: no tienen usuario y ya no se puede entrar a ellos.

Funciones dejadas a propósito para más adelante (ver la tabla en el README): escáner de cuaderno, modo sin conexión, WhatsApp, Modo Aula, recompensas de la mascota, confirmación por correo y ejercicios generados por IA.

## Flujo de trabajo con git

- Ramas: `main` (estable), `dev` (integración, rama por defecto) y una por integrante: `victor`, `gera`, `zulu`, `samuel` y `katia`.
- Cada quien trabaja en su rama → pull request a `dev` → cuando `dev` está estable, pull request de `dev` a `main`.
- Reglas activas en GitHub:
  - `main`: solo por pull request con **1 aprobación**; no se puede forzar ni borrar.
  - `dev`: solo por pull request, sin aprobación; no se puede forzar ni borrar.
- Nadie puede aprobar su propio pull request.
- Haz commit o push solo cuando el usuario lo pida. Nunca subas `.env`, `*.db` ni claves; ya están en `.gitignore`.

## Cómo correrlo

```bash
# Backend (FastAPI + SQLite). No hay python3-venv en el sistema: se usa uv.
cd backend
uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt   # solo la primera vez
cp .env.example .env                                                             # solo la primera vez
.venv/bin/uvicorn app.main:app --reload --reload-include '*.json' --env-file .env   # puerto 8000

# Frontend (React + Vite, sin librerías de interfaz)
cd frontend && npm install && npm run dev        # http://localhost:5173 (le pasa /api al 8000)

# Pruebas
cd backend && .venv/bin/python -m pytest -q
cd frontend && npm run build                     # para detectar errores de compilación
```

`--reload-include '*.json'` hace que el backend recargue al editar el contenido de los cursos. El catálogo se guarda en caché con `lru_cache`.

## Arquitectura

```
backend/app/
  courses/content/*.json  BIBLIOTECA CURRICULAR: un JSON por curso (estándar en docs/estandar-de-leccion.md)
  courses/generic.py      motor de sumas, restas, multiplicación, división, raíces y álgebra (tipos en TIPOS)
  courses/fractions_course.py  adapta fractions_engine.py y lesson.py a la interfaz Course
  courses/base.py         interfaz Course, theory(), etapas CPA, modelo de barras (bar_model) y leaks_answer()
  tutor.py                máquina de estados de la sesión, igual para todos los cursos (incluye la evaluación final)
  auth.py                 scrypt, tokens (guardados solo como hash), código de recuperación, freno de intentos
  achievements.py         logros y constancias
  teacher.py              panel docente (errores agrupados por curso, grupo demo SIMULADO)
  db.py                   todo el SQL (SQLite) y migraciones sencillas en init_db()
  ai/                     proveedor intercambiable: mock ($0, usa contenido verificado) | claude
frontend/src/
  App.jsx                 rutas con el hash (#/cursos, #/curso/ID, #/progreso, #/logros, #/reconocimientos, #/constancia/ID, #docente)
  components/LessonPage.jsx  lección: temario, teoría, pasos, botón «?», ayuda extra, ventana de teoría
  components/MathVisual.jsx  dibujos: base10, columnas, arreglo, reparto, cuadricula, balanza, modelo (+ FractionVisual)
```

Todas las acciones de una sesión devuelven la misma «vista» (`tutor._view`): fase, mensajes, ejercicio, pistas, acciones permitidas, `help` y progreso. El frontend solo pinta esa vista.

## Principios que no se negocian

1. **La IA nunca califica.** Las respuestas las revisa código determinista con pruebas. La IA solo conversa: en la teoría, en la explicación y en la ayuda extra.
2. **Nunca se entrega la respuesta final**: ni en las pistas, ni en los pasos, ni la IA. `leaks_answer` reemplaza la respuesta de la IA si la revela. El ejemplo resuelto siempre usa otros números.
3. **Leer no es opcional**: hay preguntas de comprobación de «por qué», pasos obligatorios en las pistas, predicción antes de calcular (en fracciones) y detección de respuestas al azar.
4. **El contenido va separado de la lógica**: los textos están en JSON, revisables por una docente sin programar, y los números en código.
5. **Privacidad de menores**: sin correo ni nombre real; el alumno puede borrar todos sus datos.
6. **Logros por razonamiento, no por cantidad.** Sin vidas ni castigos.
7. **Honestidad**: los datos simulados se marcan como tales, el contenido indica su estado de validación y las constancias dicen «sin valor curricular».

## Fuentes y licencias (importante)

- **SEP, programas sintéticos 2024**: solo se pueden reproducir sin fines comerciales y sin modificarlos. Se citan **fragmentos breves** como fundamento curricular; no se copia ni se adapta su texto.
- **OpenStax Prealgebra 2e**: licencia CC BY-NC-SA y **prohíbe usarlo en productos de IA generativa**. Solo sirve como lectura complementaria: **no copiar su texto ni ponerlo en prompts.**
- La teoría y los textos de ThinkLoop son **propios**. No uses Khan Academy ni libros con derechos reservados como fuente de texto.

## Cosas que ya fallaron (para no repetirlas)

- **Formularios anidados** (paso de la pista dentro del formulario de la respuesta): el navegador recarga la página. Mantenlos separados.
- **React StrictMode** monta dos veces: `LessonPage` usa un `useRef` para no iniciar la sesión dos veces.
- **Rutas con el hash**: un enlace con `href="#algo"` cambia de página. El enlace «Saltar al contenido» usa `onClick`.
- **`pkill` con un patrón que coincide con tu propio comando** mata tu shell. Corre los servidores como tareas en segundo plano.
- Para verificar en el navegador se usó Chrome sin ventana con CDP (`node --experimental-websocket`). Usa una base de datos de prueba (`THINKLOOP_DB=…`) o cuentas temporales que se borran al terminar. **No dejes cuentas de prueba en `backend/thinkloop.db`.**
- Las pruebas de `tests/test_courses.py` y `tests/test_theory.py` comprueban automáticamente:
  - el contenido: respuestas contra un cálculo independiente, pasos correctos, que ninguna pista use variables «secretas» y que las cuentas de los dibujos estén bien;
  - **si agregas contenido o un tipo nuevo, deben seguir pasando.**

## Documentos de referencia

- `README.md`: funciones, API, pantallas, fuentes y licencias, pendientes y funciones para más adelante.
- `docs/estandar-de-leccion.md`: formato de cada curso, estados de validación y tipos de ejercicio.
- `docs/leccion-fracciones.md`: diseño pedagógico de la lección de fracciones.
- Documentos de diseño del equipo, que no están en el repo: acceso gratuito con presupuesto de IA (modos 1, 2 y 3), elección de modelo (Haiku 5.5 por defecto, Sonnet 5.5 para casos excepcionales; DeepSeek tiene riesgos con las reglas del hackathon y la privacidad de menores) y biblioteca curricular con validación.
