// «Loop», la mascota guía. Nunca castiga: ante un error se pone curiosa, no triste.
// Sin premios que comprar ni vidas que perder: solo acompaña y cambia de ánimo.

const LINES = {
  neutral: "Estoy contigo. Piensa en voz alta.",
  pensando: "Mmm… vamos paso a paso.",
  feliz: "¡Eso! Lo pensaste tú.",
  animando: "¡Un error es una pista! Veamos qué pasó.",
  descanso: "Descansar también es aprender.",
  hola: "¡Hola! Soy Loop. Te ayudo a pensar, no a copiar.",
  calma: "Respira. Pensar despacio también es avanzar.",
};

export function moodFor(view) {
  if (!view) return "hola";
  if (view.status === "paused") return "descanso";
  const last = [...(view.messages || [])].reverse().find((m) => m.role === "tutor");
  switch (last?.kind) {
    case "feedback_ok": case "milestone": case "summary": return "feliz";
    case "feedback_wrong": case "warning": return "animando";
    case "hint": case "example": case "ai": return "pensando";
    case "slowdown": return "calma";
    case "empathy": return "descanso";
    case "welcome": return "hola";
    default: return view.phase === "diagnostico" ? "pensando" : "neutral";
  }
}

function Eyes({ mood }) {
  if (mood === "feliz") {
    return (
      <g fill="none" stroke="var(--mascot-ink)" strokeWidth="4" strokeLinecap="round">
        <path d="M36 50 q6 -7 12 0" /><path d="M64 50 q6 -7 12 0" />
      </g>
    );
  }
  if (mood === "descanso" || mood === "calma") {
    return (
      <g fill="none" stroke="var(--mascot-ink)" strokeWidth="4" strokeLinecap="round">
        <path d="M36 50 h12" /><path d="M64 50 h12" />
      </g>
    );
  }
  const dx = mood === "pensando" ? 3 : 0, dy = mood === "pensando" ? -3 : 0;
  return (
    <g>
      <circle cx="42" cy="50" r="8" fill="#fff" /><circle cx="70" cy="50" r="8" fill="#fff" />
      <circle cx={42 + dx} cy={50 + dy} r="4" fill="var(--mascot-ink)" />
      <circle cx={70 + dx} cy={50 + dy} r="4" fill="var(--mascot-ink)" />
      {mood === "animando" && (
        <g stroke="var(--mascot-ink)" strokeWidth="3" strokeLinecap="round">
          <path d="M34 36 l12 -3" /><path d="M78 36 l-12 -3" />
        </g>
      )}
    </g>
  );
}

function Mouth({ mood }) {
  const p = { fill: "none", stroke: "var(--mascot-ink)", strokeWidth: 4, strokeLinecap: "round" };
  if (mood === "feliz" || mood === "hola") return <path d="M42 66 q14 14 28 0" {...p} />;
  if (mood === "pensando") return <circle cx="60" cy="70" r="4" fill="var(--mascot-ink)" />;
  if (mood === "descanso" || mood === "calma") return <path d="M50 70 q6 4 12 0" {...p} />;
  return <path d="M46 68 q10 8 20 0" {...p} />;
}

export default function Mascot({ mood = "neutral", size = 72, showLine = true }) {
  return (
    <div className={`mascot mood-${mood}`}>
      <svg key={mood} className="mascot-svg" viewBox="0 0 112 112" width={size} height={size}
           role="img" aria-label={`Loop, la mascota guía (${mood})`}>
        {/* antena en forma de ∞ */}
        <path d="M56 22 c-6 -10 -18 -10 -18 -2 s12 8 18 2 c6 -6 18 -10 18 -2 s-12 8 -18 2"
              fill="none" stroke="var(--teal)" strokeWidth="4" strokeLinecap="round" />
        <ellipse cx="56" cy="62" rx="44" ry="40" fill="var(--orange)" />
        <ellipse cx="56" cy="72" rx="28" ry="22" fill="var(--mascot-belly)" />
        <circle cx="30" cy="64" r="5" fill="var(--mascot-cheek)" />
        <circle cx="82" cy="64" r="5" fill="var(--mascot-cheek)" />
        <Eyes mood={mood} />
        <Mouth mood={mood} />
        {mood === "pensando" && <circle cx="98" cy="22" r="5" fill="var(--teal)" opacity="0.7" />}
        {mood === "descanso" && (
          <text x="88" y="28" fontSize="16" fontWeight="800" fill="var(--teal)">z</text>
        )}
        {mood === "animando" && (
          <path d="M96 30 l3 7 7 3 -7 3 -3 7 -3 -7 -7 -3 7 -3z" fill="var(--teal)" />
        )}
      </svg>
      {showLine && <p className="mascot-line">{LINES[mood] ?? LINES.neutral}</p>}
    </div>
  );
}
