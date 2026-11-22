import { useEffect, useState } from "react";
import { api } from "../api.js";
import CourseCover from "./CourseCover.jsx";

const STATUS = {
  nuevo: { label: "Nuevo", cls: "" },
  en_curso: { label: "En curso", cls: "doing" },
  completado: { label: "Completado ✓", cls: "done" },
};

export default function CoursesPage({ student }) {
  const [courses, setCourses] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => { api.courses().then(setCourses).catch((e) => setError(e.message)); }, []);

  if (error) return <p className="error" role="alert">{error}</p>;
  if (!courses) return <p className="muted">Cargando cursos…</p>;

  // Recomendado: el que va en curso más reciente o, si no, el primero sin completar
  const doing = courses.filter((c) => c.status === "en_curso")
    .sort((a, b) => (b.last_activity || "").localeCompare(a.last_activity || ""))[0];
  const next = doing || courses.find((c) => c.status !== "completado");

  return (
    <>
      <div className="page-head">
        <div>
          <p className="eyebrow">Hola, {student.name}</p>
          <h1>Cursos</h1>
        </div>
        <p className="muted small page-note">De lo más básico a lo más avanzado. Puedes empezar por cualquiera.</p>
      </div>
      <ul className="course-grid">
        {courses.map((c) => {
          const st = STATUS[c.status] || STATUS.nuevo;
          return (
            <li key={c.id}>
              <a className={`course-card ${next?.id === c.id ? "recommended" : ""}`} href={`#/curso/${c.id}`}>
                <CourseCover cover={c.cover} />
                {next?.id === c.id && (
                  <span className="ribbon">{doing ? "Continúa aquí" : "Recomendado"}</span>
                )}
                <div className="course-body">
                  <div className="course-meta">
                    <span className="chip">{c.level}</span>
                    <span className={`status ${st.cls}`}>{st.label}</span>
                  </div>
                  <h2>{c.title}</h2>
                  <p className="muted small">{c.description}</p>
                  <div className="meter" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={c.progress}
                       aria-label={`Avance en ${c.title}`}>
                    <div className="meter-fill" style={{ width: `${c.progress}%` }} />
                  </div>
                  <span className="muted small">
                    {c.skills.length} habilidades · {c.progress}% dominado
                  </span>
                  <span className="review-tag" title="Contenido pendiente de revisión docente">
                    Contenido: {c.meta.estado_label.toLowerCase()}
                  </span>
                </div>
              </a>
            </li>
          );
        })}
      </ul>
    </>
  );
}
