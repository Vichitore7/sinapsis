import { useEffect, useState } from "react";
import { api } from "../api.js";
import CourseCover, { TONES } from "./CourseCover.jsx";
import Mascot from "./Mascot.jsx";

// Reconocimientos: una constancia interna por curso dominado y con la evaluación final
// aprobada. Sin valor curricular.
export default function CertificatesPage() {
  const [certs, setCerts] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { api.certificates().then(setCerts).catch((e) => setError(e.message)); }, []);

  if (error) return <p className="error" role="alert">{error}</p>;
  if (!certs) return <p className="muted">Cargando…</p>;

  return (
    <>
      <div className="page-head">
        <div>
          <p className="eyebrow">Constancias internas</p>
          <h1>Reconocimientos</h1>
        </div>
        <p className="sim-banner small" role="note">Sin valor curricular: reconocen lo que aprendiste en ThinkLoop.</p>
      </div>
      <ul className="cert-grid">
        {certs.map((c) => (
          <li key={c.course_id} className={`cert-card card ${c.earned ? "earned" : "locked"}`}>
            <div className="cert-thumb">
              <CourseCover cover={c.cover} size="sm" />
              <span className="cert-star" aria-hidden="true">{c.earned ? "★" : "☆"}</span>
            </div>
            <h2>{c.title}</h2>
            {c.earned ? (
              <>
                <p className="small muted">Obtenida el {fmtDate(c.earned_at)}</p>
                <p className="small">Evaluación final: {c.exam.score} de {c.exam.total}</p>
                <a className="secondary button-link" href={`#/constancia/${c.course_id}`}>Ver constancia</a>
              </>
            ) : (
              <>
                <div className="meter" aria-hidden="true"><div className="meter-fill" style={{ width: `${c.pct}%` }} /></div>
                <p className="small muted">{c.pct}% · se obtiene al dominar sus habilidades y aprobar la evaluación final</p>
                {c.exam?.taken > 0 && (
                  <p className="small">Último intento de la evaluación: {c.exam.score} de {c.exam.total}</p>
                )}
              </>
            )}
            <p className="tiny muted">Sin valor curricular</p>
          </li>
        ))}
      </ul>
    </>
  );
}

function fmtDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("es-MX", { day: "numeric", month: "long", year: "numeric" });
}

// Constancia imprimible (o guardable como PDF desde el navegador).
export function CertificateView({ courseId }) {
  const [cert, setCert] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api.certificates()
      .then((cs) => {
        const c = cs.find((x) => x.course_id === courseId);
        if (!c || !c.earned) setError("Esta constancia todavía no está disponible.");
        else setCert(c);
      })
      .catch((e) => setError(e.message));
  }, [courseId]);

  if (error) {
    return (
      <section className="card">
        <p className="error">{error}</p>
        <a className="link" href="#/reconocimientos">← Reconocimientos</a>
      </section>
    );
  }
  if (!cert) return <p className="muted">Cargando…</p>;
  const tone = TONES[cert.cover?.tono] || TONES.naranja;

  return (
    <>
      <div className="no-print tools cert-actions">
        <a className="link" href="#/reconocimientos">← Reconocimientos</a>
        <button className="primary" onClick={() => window.print()}>Imprimir o guardar en PDF</button>
      </div>
      <article className="certificate" style={{ "--cert-accent": tone.bg }} aria-label={`Constancia de ${cert.title}`}>
        <div className="cert-inner">
          <div className="cert-brand"><span className="logo" aria-hidden="true">∞</span> ThinkLoop</div>
          <p className="cert-kicker">Constancia de aprendizaje</p>
          <p className="cert-text">Se reconoce a</p>
          <p className="cert-name">{cert.student_name}</p>
          <p className="cert-text">por dominar, resolviendo por su cuenta, las habilidades del curso</p>
          <p className="cert-course">{cert.title}</p>
          <ul className="cert-skills">{cert.skills.map((s) => <li key={s}>{s}</li>)}</ul>
          <p className="cert-text">y aprobar su evaluación final con {cert.exam.score} de {cert.exam.total}</p>
          <div className="cert-foot">
            <span>{fmtDate(cert.earned_at)}</span>
            <Mascot mood="feliz" size={56} showLine={false} />
            <span>{cert.level}</span>
          </div>
          <p className="cert-note">{cert.note}</p>
        </div>
      </article>
    </>
  );
}
