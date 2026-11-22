import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import MathVisual from "./MathVisual.jsx";
import Mascot, { moodFor } from "./Mascot.jsx";
import CourseCover from "./CourseCover.jsx";

const KIND_LABEL = {
  hint: "Pista", example: "Ejemplo parecido", empathy: "", milestone: "¡Logro!",
  feedback_ok: "", feedback_wrong: "", warning: "", ai: "Loop", summary: "Resumen",
  slowdown: "Con calma",
};

// Pantalla de lección: temario del curso a la izquierda, conversación y ejercicio a la derecha.
export default function LessonPage({ courseId, student, setStudent }) {
  const [view, setView] = useState(null);
  const [course, setCourse] = useState(null);
  const [error, setError] = useState("");
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return; // StrictMode monta dos veces en desarrollo
    started.current = true;
    api.courses().then((cs) => setCourse(cs.find((c) => c.id === courseId) || null)).catch(() => {});
    api.startCourse(courseId).then(setView).catch((e) => setError(e.message));
  }, [courseId]);

  if (error) {
    return (
      <section className="card">
        <p className="error" role="alert">{error}</p>
        <a className="link" href="#/cursos">← Volver a cursos</a>
      </section>
    );
  }
  if (!view) return <p className="muted">Preparando tu lección…</p>;
  return <Lesson view={view} setView={setView} course={course} courseId={courseId}
                 student={student} setStudent={setStudent} />;
}

function Lesson({ view, setView, course, courseId, student, setStudent }) {
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [helpOpen, setHelpOpen] = useState(false);
  const [helpNote, setHelpNote] = useState("");
  const [theoryOpen, setTheoryOpen] = useState(false);
  const logRef = useRef(null);
  const answerRef = useRef(null);
  const sid = view.session_id;
  const paused = view.status === "paused";
  const stuck = view.help?.stuck;

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" });
  }, [view.history?.length]);

  useEffect(() => {
    setAnswer("");
    setHelpNote("");
    if (view.exercise) answerRef.current?.focus();
  }, [view.exercise?.id]);

  // Cuando se activa la ayuda extra, se abre sola
  useEffect(() => { if (stuck) { setHelpOpen(true); setHelpNote(""); } }, [stuck]);
  useEffect(() => { if (!view.help?.ai) setHelpOpen(false); }, [view.help?.ai]);

  async function run(fn) {
    setBusy(true);
    setError("");
    try { setView(await fn()); } catch (e) { setError(e.message); }
    setBusy(false);
  }

  const submitAnswer = (e) => {
    e.preventDefault();
    if (!answer.trim()) return;
    run(() => api.answer(sid, answer.trim()));
  };
  const changeStyle = async (e) => setStudent(await api.setStyle(e.target.value));
  const can = (a) => view.actions.includes(a);
  const onQuestion = () => {
    if (view.help?.ai) { setHelpOpen(!helpOpen); setHelpNote(""); }
    else setHelpNote(view.help?.locked_reason || "");
  };

  return (
    <div className="lesson-layout">
      <aside className="card outline" aria-label="Temario del curso">
        <a className="link back" href="#/cursos">← Cursos</a>
        <div className="outline-head">
          {course && <CourseCover cover={course.cover} size="sm" />}
          <h2>{view.course.title}</h2>
        </div>
        <ol className="outline-steps">
          {view.progress.skills.map((s, i) => {
            const current = s.id === view.skill && view.phase !== "cierre";
            return (
              <li key={s.id} className={`${s.mastered ? "done" : ""} ${current ? "current" : ""}`}
                  aria-current={current ? "step" : undefined}>
                <span className="node" aria-hidden="true">{s.mastered ? "✓" : i + 1}</span>
                <div className="skill-info">
                  <span className="skill-name">{s.name}</span>
                  <div className="meter small-meter"><div className="meter-fill" style={{ width: `${Math.round(s.mastery * 100)}%` }} /></div>
                  <span className="muted small">{s.mastered ? "Dominada" : current ? view.phase_label : "Pendiente"}</span>
                </div>
              </li>
            );
          })}
        </ol>
        {view.progress.errors_overcome.length > 0 && (
          <div className="overcome-box">
            <h3>Errores que dejaste atrás</h3>
            <ul className="overcome">{view.progress.errors_overcome.map((e, i) => <li key={i}>{e}</li>)}</ul>
          </div>
        )}
        {course?.has_theory && view.phase !== "fundamentos" && (
          <button className="secondary theory-btn" onClick={() => setTheoryOpen(true)}>📖 Teoría del curso</button>
        )}
        <label className="style-switch">
          <span className="small muted">Estilo de Loop</span>
          <select value={student.tutor_style} onChange={changeStyle}>
            <option value="paciente">Paciente</option>
            <option value="companero">Compañero</option>
            <option value="experto">Experto</option>
          </select>
        </label>
        {can("pause") && (
          <button className="secondary pause" onClick={() => run(() => api.pause(sid))}>
            ☕ Necesito un descanso
          </button>
        )}
      </aside>

      <section className="card lesson" aria-labelledby="lesson-title">
        <div className="lesson-head">
          <Mascot mood={moodFor(view)} size={60} />
          <div className="lesson-title">
            <p className="eyebrow">{view.phase_label}</p>
            <h1 id="lesson-title">
              {view.skill_name || (view.phase === "fundamentos" ? "Teoría del curso"
                : view.phase === "cierre" ? "¡Curso terminado!" : view.course.title)}
            </h1>
          </div>
        </div>

        <div className="log" ref={logRef} aria-live="polite" aria-label="Conversación con Loop">
          {(view.history || []).map((m, i) => (
            <div key={i} className={`bubble ${m.role} ${m.kind}`}>
              {KIND_LABEL[m.kind] && <span className="bubble-label">{KIND_LABEL[m.kind]}</span>}
              {m.text}
              {m.visual && <MathVisual visual={m.visual} />}
            </div>
          ))}
        </div>

        {paused ? (
          <div className="paused">
            <p>Tu sesión está en pausa. Tu lugar está guardado.</p>
            <button className="primary" onClick={() => run(() => api.startCourse(courseId))}>Volver a la lección</button>
            <DemoReturn onReturn={(d) => run(() => api.startCourse(courseId, d))} />
          </div>
        ) : (
          <>
            {view.theory && (
              <Theory theory={view.theory} busy={busy} onAsk={() => setHelpOpen(true)}
                      onCheck={(opt) => run(() => api.theory(sid, opt))} />
            )}

            {view.explanation && (
              <Explanation key={view.skill} exp={view.explanation} busy={busy}
                           onCheck={(opt) => run(() => api.check(sid, opt))}
                           onAsk={() => setHelpOpen(true)} />
            )}

            {view.exercise && view.prediction && (
              <div className="exercise">
                <p className="prompt">{view.exercise.prompt}</p>
                <MathVisual visual={view.exercise.visual} />
                <div className="predict">
                  <p className="predict-q"><strong>Antes de calcular…</strong> {view.prediction.question}</p>
                  <div className="tools">
                    {view.prediction.options.map((o) => (
                      <button key={o.id} type="button" className="secondary big-choice" disabled={busy}
                              onClick={() => run(() => api.predict(sid, o.id))}>{o.text}</button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {view.exercise && !view.prediction && (
              <div className="exercise">
                {/* Ojo: el formulario de la respuesta NO debe envolver al del mini paso
                    (formularios anidados = el navegador recarga la página al enviar). */}
                <form onSubmit={submitAnswer}>
                  <p className="prompt" id="prompt">{view.exercise.prompt}</p>
                  <MathVisual visual={view.exercise.visual} />
                  <label htmlFor="answer" className="small muted">{view.exercise.input_hint}</label>
                  <div className="answer-row">
                    <input id="answer" ref={answerRef} value={answer} inputMode="text"
                           autoComplete="off" aria-describedby="prompt" maxLength={40}
                           onChange={(e) => setAnswer(e.target.value)} placeholder="Tu respuesta" />
                    <button className="primary" disabled={busy || !answer.trim()}>Comprobar</button>
                    {view.phase !== "diagnostico" && (
                      <button type="button" className={`help-btn ${view.help?.ai ? "on" : ""}`}
                              aria-expanded={helpOpen} aria-controls="help-panel" onClick={onQuestion}
                              title={view.help?.ai ? "Ayuda extra de Loop" : view.help?.locked_reason}
                              aria-label={view.help?.ai ? "Abrir ayuda extra de Loop" : "Ayuda extra (bloqueada)"}>
                        ?
                      </button>
                    )}
                  </div>
                </form>
                {helpNote && !view.help?.ai && (
                  <p className="help-note" role="status">
                    🔒 {helpNote} {can("hint") && "Prueba primero con una pista."}
                  </p>
                )}
                {view.step && (
                  <StepForm key={`${view.exercise.id}-${view.hints.shown}`} step={view.step} busy={busy}
                            onSubmit={(vals) => run(() => api.step(sid, vals))} />
                )}
                <div className="tools">
                  {can("hint") && (
                    <button type="button" className="secondary" disabled={busy} onClick={() => run(() => api.hint(sid))}>
                      Pedir pista ({view.hints.shown + 1} de {view.hints.total})
                    </button>
                  )}
                  {!can("hint") && view.hints.total > 0 && view.phase === "practica" && !view.step &&
                    view.hints.shown < view.hints.total && (
                    <span className="muted small">Responde el paso para ver la siguiente pista.</span>
                  )}
                  {can("dont_know") && (
                    <button type="button" className="secondary" disabled={busy} onClick={() => run(() => api.dontKnow(sid))}>
                      No lo sé todavía
                    </button>
                  )}
                </div>
              </div>
            )}

            {helpOpen && view.help?.ai && (
              <HelpPanel view={view} busy={busy} stuck={stuck}
                         onAsk={(text) => run(() => api.message(sid, text))}
                         onExample={() => run(() => api.example(sid))}
                         onSkip={() => run(() => api.skip(sid))}
                         onClose={() => setHelpOpen(false)} />
            )}

            {view.phase === "cierre" && (
              <div className="closing">
                <a className="primary button-link" href="#/cursos">Elegir otro curso</a>
                <a className="secondary button-link" href="#/reconocimientos">Ver mis reconocimientos</a>
                <button className="link" onClick={() => run(() => api.startCourse(courseId))}>Practicar de nuevo</button>
                <DemoReturn onReturn={(d) => run(() => api.startCourse(courseId, d))} />
              </div>
            )}

            {error && <p className="error" role="alert">{error}</p>}
          </>
        )}
      </section>
      {theoryOpen && <TheoryModal courseId={courseId} onClose={() => setTheoryOpen(false)} />}
    </div>
  );
}

// Teoría del curso: una idea por tarjeta, con dibujo; al final, una pregunta de «por qué».
function Theory({ theory, busy, onCheck, onAsk }) {
  const [i, setI] = useState(0);
  const cards = theory.cards;
  const atCheck = i >= cards.length;
  const card = cards[Math.min(i, cards.length - 1)];
  return (
    <div className="theory">
      <p className="eyebrow">Teoría · {theory.title}</p>
      {!atCheck ? (
        <>
          <h2>{card.title}</h2>
          <p className="theory-text" aria-live="polite">{card.text}</p>
          <MathVisual visual={card.visual} />
          <div className="dots" aria-label={`Tarjeta ${i + 1} de ${cards.length}`}>
            {cards.map((_, k) => <span key={k} className={k <= i ? "on" : ""} />)}
          </div>
          <div className="tools">
            {i > 0 && <button className="secondary" onClick={() => setI(i - 1)}>← Atrás</button>}
            <button className="primary" onClick={() => setI(i + 1)}>{i === cards.length - 1 ? "Ya lo leí" : "Siguiente →"}</button>
            <button type="button" className="help-btn on" onClick={onAsk} aria-label="Preguntarle a Loop">?</button>
          </div>
        </>
      ) : (
        <div className="check">
          <p className="predict-q"><strong>Para comprobar que se entendió el porqué:</strong> {theory.question.question}</p>
          <div className="choices">
            {theory.question.options.map((o) => (
              <button key={o.id} className="secondary choice" disabled={busy} onClick={() => onCheck(o.id)}>{o.text}</button>
            ))}
          </div>
          <button className="link" onClick={() => setI(0)}>Volver a leer la teoría</button>
        </div>
      )}
      <Sources sources={theory.sources} />
    </div>
  );
}

function Sources({ sources }) {
  if (!sources?.length) return null;
  return (
    <details className="sources">
      <summary className="small">¿De dónde sale esto? (fuentes)</summary>
      <ul>
        {sources.map((s, k) => (
          <li key={k} className="small">
            <a href={s.url} target="_blank" rel="noreferrer">{s.titulo}</a>
            {s.cita && <q>{s.cita}</q>}
            <span className="muted"> {s.uso}</span>
          </li>
        ))}
      </ul>
    </details>
  );
}

// Para releer la teoría en cualquier momento, sin salir de la lección.
function TheoryModal({ courseId, onClose }) {
  const [th, setTh] = useState(null);
  const ref = useRef(null);
  useEffect(() => {
    api.course(courseId).then((c) => setTh(c.theory)).catch(() => setTh(false));
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    ref.current?.focus();
    return () => document.removeEventListener("keydown", onKey);
  }, [courseId, onClose]);
  return (
    <div className="modal-back" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal card" role="dialog" aria-modal="true" aria-label="Teoría del curso" tabIndex={-1} ref={ref}>
        <div className="help-head">
          <strong>📖 {th ? th.title : "Teoría del curso"}</strong>
          <button className="link" onClick={onClose}>Cerrar</button>
        </div>
        {th === null && <p className="muted">Cargando…</p>}
        {th === false && <p className="error">No se pudo cargar la teoría.</p>}
        {th && (
          <>
            <p className="muted">{th.intro}</p>
            {th.cards.map((c, k) => (
              <section key={k} className="theory-card">
                <h3>{k + 1}. {c.title}</h3>
                <p>{c.text}</p>
                <MathVisual visual={c.visual} />
              </section>
            ))}
            <Sources sources={th.sources} />
          </>
        )}
      </div>
    </div>
  );
}

// Ayuda extra: solo cuando las pistas no bastaron (o mientras se lee una explicación).
function HelpPanel({ view, busy, stuck, onAsk, onExample, onSkip, onClose }) {
  const [text, setText] = useState("");
  const inputRef = useRef(null);
  useEffect(() => { inputRef.current?.focus(); }, []);
  const send = (e) => {
    e.preventDefault();
    if (!text.trim()) return;
    onAsk(text.trim());
    setText("");
  };
  return (
    <div className="help-panel" id="help-panel" role="region" aria-label="Ayuda extra de Loop">
      <div className="help-head">
        <strong>{stuck ? "Ayuda extra" : "Pregúntale a Loop"}</strong>
        <button type="button" className="link" onClick={onClose}>Cerrar</button>
      </div>
      <p className="small muted">
        {stuck ? "Loop te lo explica de otra forma, adaptado a ti. No te dará la respuesta: el último paso es tuyo."
               : "¿Algo no te quedó claro? Pregúntalo con tus palabras."}
      </p>
      <form className="chat" onSubmit={send}>
        <label htmlFor="chat" className="sr-only">Tu pregunta para Loop</label>
        <input id="chat" ref={inputRef} value={text} onChange={(e) => setText(e.target.value)} maxLength={500}
               placeholder={stuck ? "¿Qué parte no entiendes?" : "Escribe tu duda"} />
        <button className="primary" disabled={busy || !text.trim()}>Preguntar</button>
      </form>
      {stuck && view.actions.includes("example") && (
        <div className="tools">
          <button type="button" className="secondary" disabled={busy} onClick={onExample}>Ver un ejemplo parecido</button>
          <button type="button" className="secondary" disabled={busy} onClick={onSkip}>Probar con otro ejercicio</button>
        </div>
      )}
    </div>
  );
}

// Explicación en pantallas cortas: una idea a la vez y, al final, una pregunta para comprobar.
function Explanation({ exp, busy, onCheck, onAsk }) {
  const [i, setI] = useState(0);
  const last = exp.body.length - 1;
  const atCheck = i > last;
  return (
    <div className="explanation">
      <h2>{exp.title}</h2>
      <MathVisual visual={exp.visual} />
      {!atCheck ? (
        <>
          <p className="idea" aria-live="polite">{exp.body[i]}</p>
          <div className="dots" aria-label={`Idea ${i + 1} de ${exp.body.length}`}>
            {exp.body.map((_, k) => <span key={k} className={k <= i ? "on" : ""} />)}
          </div>
          <div className="tools">
            {i > 0 && <button className="secondary" onClick={() => setI(i - 1)}>← Atrás</button>}
            <button className="primary" onClick={() => setI(i + 1)}>{i === last ? "Ya lo leí" : "Siguiente →"}</button>
            <button type="button" className="help-btn on" onClick={onAsk} aria-label="Preguntarle a Loop">?</button>
          </div>
        </>
      ) : (
        <div className="check">
          <p className="why"><strong>¿Por qué funciona?</strong> {exp.why}</p>
          <p className="predict-q"><strong>Antes de practicar:</strong> {exp.check.question}</p>
          <div className="choices">
            {exp.check.options.map((o) => (
              <button key={o.id} className="secondary choice" disabled={busy} onClick={() => onCheck(o.id)}>{o.text}</button>
            ))}
          </div>
          <button className="link" onClick={() => setI(0)}>Volver a leer las ideas</button>
        </div>
      )}
    </div>
  );
}

// Mini paso de una pista: se responde para poder pedir la siguiente.
function StepForm({ step, busy, onSubmit }) {
  const [vals, setVals] = useState(step.fields.map(() => ""));
  const set = (k, v) => setVals(vals.map((x, j) => (j === k ? v : x)));
  const ready = vals.every((v) => v.trim());
  return (
    <form className="step" onSubmit={(e) => { e.preventDefault(); if (ready) onSubmit(vals); }}>
      <p className="small"><strong>{step.prompt}</strong></p>
      {step.fields.map((f, k) => (
        <div key={k} className="step-field">
          <span>{f.label}</span>
          {f.options ? (
            <div className="tools">
              {f.options.map((o) => (
                <button key={o} type="button" disabled={busy}
                        className={`secondary ${vals[k] === o ? "selected" : ""}`}
                        onClick={() => (step.fields.length === 1 ? onSubmit([o]) : set(k, o))}>{o}</button>
              ))}
            </div>
          ) : (
            <input value={vals[k]} onChange={(e) => set(k, e.target.value)} inputMode="numeric"
                   autoComplete="off" maxLength={20} aria-label={f.label} />
          )}
        </div>
      ))}
      {!(step.fields.length === 1 && step.fields[0].options) && (
        <button className="secondary" disabled={busy || !ready}>Responder paso</button>
      )}
    </form>
  );
}

// Solo para la demo del hackathon: simular que el alumno regresa meses después.
function DemoReturn({ onReturn }) {
  return (
    <details className="demo">
      <summary className="small muted">Demo: simular regreso</summary>
      <button type="button" className="link" onClick={() => onReturn(60)}>Regresar como si pasaran 2 meses</button>
    </details>
  );
}
