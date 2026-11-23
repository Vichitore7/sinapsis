import { useEffect, useState } from "react";
import { api } from "../api.js";
import CourseCover from "./CourseCover.jsx";

// Progreso por curso: porcentaje dominado, habilidades y errores que se dejaron atrás.
export default function ProgressPage() {
  const [progress, setProgress] = useState(null);
  const [courses, setCourses] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.progress(), api.courses()])
      .then(([p, c]) => { setProgress(p); setCourses(c); })
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="error" role="alert">{error}</p>;
  if (!progress) return <p className="muted">Cargando tu progreso…</p>;

  const byId = Object.fromEntries(courses.map((c) => [c.id, c]));
  const started = progress.filter((p) => p.skills.some((s) => s.attempts > 0 || s.mastered));
  const rest = progress.filter((p) => !started.includes(p));

  return (
    <>
      <div className="page-head">
        <div>
          <p className="eyebrow">Tu camino</p>
          <h1>Progreso</h1>
        </div>
        <p className="muted small page-note">Una habilidad se domina cuando la resuelves por tu cuenta, no por hacer muchos ejercicios. Cada curso cierra con una evaluación final.</p>
      </div>
      {started.length === 0 && (
        <section className="card empty">
          <p>Todavía no empiezas ningún curso. <a className="link" href="#/cursos">Elige uno</a> y aquí verás tu avance.</p>
        </section>
      )}
      <ul className="progress-grid">
        {started.map((p) => (
          <li key={p.course.id} className="card progress-card">
            <div className="progress-top">
              <CourseCover cover={byId[p.course.id]?.cover} size="sm" />
              <div className="progress-title">
                <h2>{p.course.title}</h2>
                <span className="pct-big">{p.pct}%</span>
              </div>
            </div>
            <div className="meter" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={p.pct}
                 aria-label={`Dominio de ${p.course.title}`}>
              <div className="meter-fill" style={{ width: `${p.pct}%` }} />
            </div>
            <ul className="skill-list">
              {p.skills.map((s) => (
                <li key={s.id} className={s.mastered ? "done" : ""}>
                  <span aria-hidden="true">{s.mastered ? "✓" : "○"}</span> {s.name}
                  <span className="muted small"> · {s.mastered ? "dominada" : s.attempts ? "practicando" : "pendiente"}</span>
                </li>
              ))}
            </ul>
            <p className={`small exam-line ${p.exam.passed ? "done" : ""}`}>
              <span aria-hidden="true">{p.exam.passed ? "★" : "☆"}</span> Evaluación final:{" "}
              {p.exam.passed ? `aprobada con ${p.exam.score} de ${p.exam.total}`
                : p.exam.taken ? `${p.exam.score} de ${p.exam.total} en el último intento (necesitas ${p.exam.pass_mark})`
                : "al terminar las habilidades"}
            </p>
            {p.errors_overcome.length > 0 && (
              <p className="small overcome-line">💪 Dejaste atrás: {p.errors_overcome.join("; ")}</p>
            )}
            <a className="link" href={`#/curso/${p.course.id}`}>{p.completed ? "Repasar" : "Continuar"} →</a>
          </li>
        ))}
      </ul>
      {rest.length > 0 && started.length > 0 && (
        <p className="muted small">Cursos sin empezar: {rest.map((p) => p.course.title).join(", ")}.</p>
      )}
    </>
  );
}
