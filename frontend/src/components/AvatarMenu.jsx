import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";

const STYLES = [
  { id: "paciente", label: "Profesor paciente" },
  { id: "companero", label: "Compañero cercano" },
  { id: "experto", label: "Experto directo" },
];

// Avatar (inicial del apodo) arriba a la derecha, con el menú de la cuenta.
export default function AvatarMenu({ student, onStudent, onLogout, onDelete }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e) => { if (!ref.current?.contains(e.target)) setOpen(false); };
    const onKey = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDoc); document.removeEventListener("keydown", onKey); };
  }, [open]);

  async function changeStyle(e) {
    onStudent(await api.setStyle(e.target.value));
  }

  const initial = (student.name || "?").trim().charAt(0).toUpperCase();
  return (
    <div className="avatar-menu" ref={ref}>
      <button className="avatar" aria-haspopup="true" aria-expanded={open}
              aria-label={`Tu cuenta: ${student.name}`} onClick={() => setOpen(!open)}>
        {initial}
      </button>
      {open && (
        <div className="menu" role="menu">
          <p className="menu-name">{student.name}</p>
          <p className="muted small menu-sub">Sin correo ni datos personales</p>
          <label className="menu-field">
            <span className="small">Cómo te enseña Loop</span>
            <select value={student.tutor_style} onChange={changeStyle}>
              {STYLES.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
            </select>
          </label>
          <button role="menuitem" className="menu-item" onClick={onLogout}>Cerrar sesión</button>
          <button role="menuitem" className="menu-item danger" onClick={onDelete}>Borrar mis datos</button>
        </div>
      )}
    </div>
  );
}
