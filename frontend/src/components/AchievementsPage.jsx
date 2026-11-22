import { useEffect, useState } from "react";
import { api } from "../api.js";

// Logros: premian CÓMO piensas (corregir tus errores, estimar, ir paso a paso),
// no cuántos ejercicios haces.
export default function AchievementsPage() {
  const [items, setItems] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { api.achievements().then(setItems).catch((e) => setError(e.message)); }, []);

  if (error) return <p className="error" role="alert">{error}</p>;
  if (!items) return <p className="muted">Cargando tus logros…</p>;
  const earned = items.filter((a) => a.earned).length;

  return (
    <>
      <div className="page-head">
        <div>
          <p className="eyebrow">{earned} de {items.length}</p>
          <h1>Logros</h1>
        </div>
        <p className="muted small page-note">Aquí no cuenta cuántos ejercicios haces, sino cómo los piensas.</p>
      </div>
      <ul className="achievement-list">
        {items.map((a) => (
          <li key={a.id} className={`achievement ${a.earned ? "earned" : "locked"}`}>
            <span className="ach-icon" aria-hidden="true">{a.earned ? a.icon : "?"}</span>
            <div>
              <h2>{a.title}</h2>
              <p className="small">{a.desc}</p>
              <span className="muted small">
                {a.earned ? `Lo lograste el ${new Date(a.earned_at).toLocaleDateString("es-MX")}` : "Todavía no"}
              </span>
            </div>
          </li>
        ))}
      </ul>
    </>
  );
}
