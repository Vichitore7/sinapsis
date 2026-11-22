import { useState } from "react";
import { api } from "../api.js";
import Mascot from "./Mascot.jsx";

const STYLES = [
  { id: "paciente", label: "Profesor paciente", desc: "Explica con calma y te anima mucho." },
  { id: "companero", label: "Compañero cercano", desc: "Como un amigo que ya entendió el tema." },
  { id: "experto", label: "Experto directo", desc: "Breve y al grano." },
];

// Entrar / crear cuenta / recuperar acceso. Sin correo ni nombre real:
// solo un apodo y una contraseña, más un código de recuperación.
export default function AuthScreen({ onAuth }) {
  const [mode, setMode] = useState("entrar");
  const [pending, setPending] = useState(null); // {token, student, recovery_code} por confirmar

  if (pending) {
    return <RecoveryCode data={pending} onDone={() => onAuth(pending)} />;
  }
  return (
    <section className="card auth-card">
      <Mascot mood="hola" size={92} />
      <h1>Aprende a pensar, no solo a obtener respuestas</h1>
      <div className="tabs" role="tablist" aria-label="Acceso">
        {[["entrar", "Entrar"], ["crear", "Crear cuenta"]].map(([id, label]) => (
          <button key={id} role="tab" aria-selected={mode === id} className={`tab ${mode === id ? "on" : ""}`}
                  onClick={() => setMode(id)}>{label}</button>
        ))}
      </div>
      {mode === "entrar" && <LoginForm onAuth={onAuth} onForgot={() => setMode("recuperar")} />}
      {mode === "crear" && <RegisterForm onCreated={setPending} />}
      {mode === "recuperar" && <ResetForm onReset={setPending} onBack={() => setMode("entrar")} />}
      <p className="privacy small muted">
        🔒 No pedimos correo, teléfono ni tu nombre completo. Usa un apodo.
      </p>
    </section>
  );
}

function useSubmit() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function run(fn) {
    setBusy(true); setError("");
    try { await fn(); } catch (e) { setError(e.message); }
    setBusy(false);
  }
  return { busy, error, run };
}

function PasswordInput({ id, value, onChange, autoComplete }) {
  const [show, setShow] = useState(false);
  return (
    <div className="password-row">
      <input id={id} type={show ? "text" : "password"} value={value} onChange={(e) => onChange(e.target.value)}
             autoComplete={autoComplete} minLength={6} maxLength={64} required />
      <button type="button" className="secondary small-btn" onClick={() => setShow(!show)}
              aria-label={show ? "Ocultar contraseña" : "Mostrar contraseña"}>{show ? "Ocultar" : "Ver"}</button>
    </div>
  );
}

function LoginForm({ onAuth, onForgot }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const { busy, error, run } = useSubmit();
  return (
    <form onSubmit={(e) => { e.preventDefault(); run(async () => onAuth(await api.login(username.trim(), password))); }}>
      <label htmlFor="l-user">Usuario</label>
      <input id="l-user" value={username} onChange={(e) => setUsername(e.target.value)}
             autoComplete="username" maxLength={20} required />
      <label htmlFor="l-pass">Contraseña</label>
      <PasswordInput id="l-pass" value={password} onChange={setPassword} autoComplete="current-password" />
      {error && <p className="error" role="alert">{error}</p>}
      <button className="primary big" disabled={busy || !username.trim() || !password}>
        {busy ? "Entrando…" : "Entrar"}
      </button>
      <button type="button" className="link" onClick={onForgot}>Olvidé mi contraseña</button>
    </form>
  );
}

function RegisterForm({ onCreated }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [group, setGroup] = useState("");
  const [style, setStyle] = useState("paciente");
  const { busy, error, run } = useSubmit();
  const validUser = /^[A-Za-z0-9_.-]{3,20}$/.test(username.trim());
  return (
    <form onSubmit={(e) => {
      e.preventDefault();
      run(async () => onCreated(await api.register(username.trim(), password, style, group.trim() || null)));
    }}>
      <label htmlFor="r-user">Elige un apodo de usuario</label>
      <input id="r-user" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username"
             maxLength={20} placeholder="Por ejemplo: tigre_azul" aria-describedby="r-user-help" required />
      <p id="r-user-help" className="muted small field-help">
        De 3 a 20 caracteres: letras, números, punto o guion. No uses tu nombre completo.
      </p>
      <label htmlFor="r-pass">Contraseña</label>
      <PasswordInput id="r-pass" value={password} onChange={setPassword} autoComplete="new-password" />
      <p className="muted small field-help">Mínimo 6 caracteres.</p>

      <label htmlFor="r-group">Código de grupo <span className="muted small">(opcional, si tu profe te dio uno)</span></label>
      <input id="r-group" value={group} onChange={(e) => setGroup(e.target.value)}
             maxLength={12} autoComplete="off" placeholder="Por ejemplo: 1A-MATE" />

      <fieldset>
        <legend>¿Cómo prefieres que te enseñe Loop?</legend>
        <div className="style-options">
          {STYLES.map((s) => (
            <label key={s.id} className={`style-option ${style === s.id ? "selected" : ""}`}>
              <input type="radio" name="style" value={s.id} checked={style === s.id} onChange={() => setStyle(s.id)} />
              <span className="style-label">{s.label}</span>
              <span className="style-desc">{s.desc}</span>
            </label>
          ))}
        </div>
      </fieldset>
      {error && <p className="error" role="alert">{error}</p>}
      <button className="primary big" disabled={busy || !validUser || password.length < 6}>
        {busy ? "Creando…" : "Crear mi cuenta"}
      </button>
    </form>
  );
}

function ResetForm({ onReset, onBack }) {
  const [username, setUsername] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const { busy, error, run } = useSubmit();
  return (
    <form onSubmit={(e) => { e.preventDefault(); run(async () => onReset(await api.reset(username.trim(), code.trim(), password))); }}>
      <p className="muted">Usa el código de recuperación que guardaste al crear tu cuenta.</p>
      <label htmlFor="x-user">Usuario</label>
      <input id="x-user" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
      <label htmlFor="x-code">Código de recuperación</label>
      <input id="x-code" value={code} onChange={(e) => setCode(e.target.value)} autoComplete="off"
             placeholder="XXXX-XXXX-XXXX" maxLength={20} required />
      <label htmlFor="x-pass">Nueva contraseña</label>
      <PasswordInput id="x-pass" value={password} onChange={setPassword} autoComplete="new-password" />
      {error && <p className="error" role="alert">{error}</p>}
      <button className="primary big" disabled={busy || !username.trim() || !code.trim() || password.length < 6}>
        Cambiar contraseña
      </button>
      <button type="button" className="link" onClick={onBack}>Volver a entrar</button>
    </form>
  );
}

// Se muestra UNA vez: es la única forma de recuperar la cuenta sin correo.
function RecoveryCode({ data, onDone }) {
  const [saved, setSaved] = useState(false);
  const [copied, setCopied] = useState(false);
  async function copy() {
    try { await navigator.clipboard.writeText(data.recovery_code); setCopied(true); } catch { /* sin portapapeles */ }
  }
  return (
    <section className="card auth-card">
      <Mascot mood="feliz" size={80} />
      <h1>¡Listo, {data.student.name}!</h1>
      <p>Guarda este <strong>código de recuperación</strong>. Si olvidas tu contraseña, es la única forma de
        recuperar tu cuenta, porque no te pedimos correo.</p>
      <p className="recovery-code" aria-label="Código de recuperación">{data.recovery_code}</p>
      <div className="tools center-tools">
        <button className="secondary" onClick={copy}>{copied ? "¡Copiado!" : "Copiar código"}</button>
      </div>
      <p className="muted small">Anótalo en tu cuaderno o pídele a alguien de confianza que lo guarde.
        No se lo compartas a nadie más.</p>
      <label className="check-row">
        <input type="checkbox" checked={saved} onChange={(e) => setSaved(e.target.checked)} />
        Ya guardé mi código
      </label>
      <button className="primary big" disabled={!saved} onClick={onDone}>Empezar</button>
    </section>
  );
}
