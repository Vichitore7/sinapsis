import { useEffect, useState } from "react";
import { api } from "../api.js";

// Panel docente: reporte de un minuto con los errores de razonamiento agrupados.
// Se calcula sin IA a partir de los intentos guardados.

const PIN_KEY = "thinkloop.teacherPin";
const readPin = () => { try { return sessionStorage.getItem(PIN_KEY) || ""; } catch { return ""; } };
const savePin = (p) => { try { sessionStorage.setItem(PIN_KEY, p); } catch { /* sin almacenamiento */ } };

export default function TeacherDashboard() {
  const [pin, setPin] = useState(readPin);
  const [authed, setAuthed] = useState(false);
  const [groups, setGroups] = useState([]);
  const [code, setCode] = useState("");
  const [courses, setCourses] = useState([]);
  const [course, setCourse] = useState("MAT-FRAC");
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function run(fn) {
    setBusy(true); setError("");
    try { await fn(); } catch (e) { setError(e.message); }
    setBusy(false);
  }

  const login = (p = pin) => run(async () => {
    setGroups(await api.teacherGroups(p));
    setCourses(await api.teacherCourses(p));
    savePin(p);
    setAuthed(true);
  });

  useEffect(() => { if (pin) login(pin); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const open = (c, crs = course) => run(async () => { setReport(await api.teacherGroup(pin, c, crs)); setCode(c); });
  const changeCourse = (e) => {
    setCourse(e.target.value);
    if (report) open(report.group, e.target.value);
  };
  const demo = () => run(async () => {
    const r = await api.teacherDemo(pin);
    setReport(r); setCode(r.group); setCourse(r.course.id);
    setGroups(await api.teacherGroups(pin));
  });

  if (!authed) {
    return (
      <section className="card welcome-card">
        <h1>Panel docente</h1>
        <p className="muted">Mira en un minuto dónde se atora tu grupo, sin revisar libreta por libreta.</p>
        <form onSubmit={(e) => { e.preventDefault(); login(); }}>
          <label htmlFor="pin">PIN docente</label>
          <input id="pin" type="password" inputMode="numeric" value={pin}
                 onChange={(e) => setPin(e.target.value)} autoComplete="off" />
          <p className="muted small">En la demo el PIN es 1234.</p>
          {error && <p className="error" role="alert">{error}</p>}
          <button className="primary big" disabled={busy || !pin}>Entrar</button>
        </form>
      </section>
    );
  }

  return (
    <div className="teacher">
      <section className="card teacher-bar">
        <form className="answer-row" onSubmit={(e) => { e.preventDefault(); if (code.trim()) open(code.trim()); }}>
          <label htmlFor="gcode" className="sr-only">Código de grupo</label>
          <input id="gcode" value={code} onChange={(e) => setCode(e.target.value)} placeholder="Código de grupo" />
          <button className="primary" disabled={busy || !code.trim()}>Ver grupo</button>
        </form>
        <label className="course-select">
          <span className="small muted">Curso</span>
          <select value={course} onChange={changeCourse}>
            {courses.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
          </select>
        </label>
        <div className="tools">
          {groups.map((g) => (
            <button key={g.group_code} className="secondary" onClick={() => open(g.group_code)}>
              {g.group_code} · {g.n} {g.simulated ? "(simulado)" : ""}
            </button>
          ))}
          <button className="secondary" onClick={demo} disabled={busy}>Cargar grupo de ejemplo (simulado)</button>
        </div>
        {error && <p className="error" role="alert">{error}</p>}
      </section>

      {report && <Report report={report} onRefresh={() => open(report.group)} busy={busy} />}
    </div>
  );
}

function Report({ report, onRefresh, busy }) {
  const r = report;
  return (
    <>
      {r.simulated && (
        <p className="sim-banner" role="note">
          Datos simulados para la demostración. No son resultados reales de alumnos.
        </p>
      )}
      <section className="card headline">
        <div className="lesson-head">
          <div>
            <p className="eyebrow">Grupo {r.group} · {r.course.title}</p>
            <h1>Reporte de un minuto</h1>
          </div>
          <button className="secondary" onClick={onRefresh} disabled={busy}>Actualizar</button>
        </div>
        <p className="headline-text">{r.headline}</p>
        <p className="muted small">
          {r.students_total} alumnos · {r.students_active} con actividad · {r.completed} terminaron la lección
        </p>
      </section>

      <div className="session-grid">
        <section className="card">
          <h2>Errores de razonamiento del grupo</h2>
          {r.misconceptions.length === 0 && <p className="muted">Sin errores frecuentes todavía.</p>}
          <ol className="miscon-list">
            {r.misconceptions.map((m) => (
              <li key={m.id}>
                <div className="miscon-head">
                  <span className="skill-name">{m.label}</span>
                  <span className="pct">{m.pct}%</span>
                </div>
                <div className="meter" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={m.pct}
                     aria-label={m.label}>
                  <div className="meter-fill warn" style={{ width: `${m.pct}%` }} />
                </div>
                <span className="muted small">{m.students} de {r.students_total} alumnos · {m.times} {m.times === 1 ? "vez" : "veces"}</span>
                <details>
                  <summary className="small">Qué hacer en clase</summary>
                  <p className="small">{m.action}</p>
                </details>
              </li>
            ))}
          </ol>
          <p className="muted small">Sugerencias en borrador, pendientes de revisión docente.</p>
        </section>

        <aside className="card">
          <h2>Dominio por habilidad</h2>
          <ol className="skill-tree">
            {r.skills.map((s) => (
              <li key={s.id} className="skill">
                <div className="skill-info">
                  <span className="skill-name">{s.name}</span>
                  <div className="meter"><div className="meter-fill" style={{ width: `${s.pct}%` }} /></div>
                  <span className="muted small">{s.mastered} de {r.students_total} la dominan</span>
                </div>
              </li>
            ))}
          </ol>

          <h3>Alumnos para acompañar</h3>
          {r.attention.length === 0 ? <p className="muted small">Nadie por ahora.</p> : (
            <ul className="attention">
              {r.attention.map((s) => (
                <li key={s.id}><strong>{s.name}</strong>: {s.needs_attention.join(", ")}.</li>
              ))}
            </ul>
          )}
        </aside>
      </div>

      <section className="card">
        <details>
          <summary><strong>Detalle por alumno</strong></summary>
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Alumno</th><th>Va en</th><th>Dominadas</th><th>Aciertos</th><th>Pistas</th><th>Error principal</th></tr>
              </thead>
              <tbody>
                {r.students.map((s) => (
                  <tr key={s.id}>
                    <td>{s.name}</td>
                    <td>{s.completed ? "Terminó" : s.current_skill ?? "—"}</td>
                    <td>{s.mastered}/{r.skills.length}</td>
                    <td>{s.accuracy == null ? "—" : `${Math.round(s.accuracy * 100)}%`}</td>
                    <td>{s.hints_used}</td>
                    <td className="small">{s.errors[0] ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </section>
    </>
  );
}
