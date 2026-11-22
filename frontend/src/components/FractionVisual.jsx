// Barras de fracciones en SVG (método CPA: primero se VE, luego se calcula).
// Son ligeras y se leen bien en celulares económicos.

const TONES = {
  a: "var(--orange)",
  b: "var(--teal)",
  ok: "var(--ok)",
  warn: "var(--warn)",
  soft: "var(--orange-soft)",
};

function Bar({ num, den, label, tone = "a", group = 1 }) {
  const w = 240, h = 28;
  const cell = w / den;
  const gap = den > 18 ? 0.6 : 1;
  // Si la fracción es mayor que 1 se dibujan varias barras (enteros + resto)
  const wholes = Math.max(1, Math.ceil(num / den));
  return (
    <figure className="fbar">
      {Array.from({ length: wholes }).map((_, wi) => {
        const filled = Math.min(den, Math.max(0, num - wi * den));
        return (
          <svg key={wi} viewBox={`0 0 ${w} ${h}`} width="100%" height={h} role="img"
               aria-label={`${label ?? ""}: ${num} de ${den} partes`}>
            {Array.from({ length: den }).map((_, i) => (
              <rect key={i} x={i * cell + gap} y={1} width={Math.max(cell - 2 * gap, 0.5)} height={h - 2}
                    rx={den > 18 ? 1 : 4} fill={i < filled ? TONES[tone] : "var(--bar-empty)"}
                    stroke="var(--bar-stroke)" strokeWidth={den > 18 ? 0.5 : 1} />
            ))}
            {group > 1 && Array.from({ length: den / group - 1 }).map((_, j) => (
              <line key={`g${j}`} x1={(j + 1) * group * cell} x2={(j + 1) * group * cell} y1={0} y2={h}
                    stroke="var(--text)" strokeWidth={2.5} />
            ))}
          </svg>
        );
      })}
      <figcaption>{label ?? `${num}/${den}`}</figcaption>
    </figure>
  );
}

export default function FractionVisual({ visual }) {
  if (!visual) return null;
  if (visual.kind === "barras") {
    return (
      <div className="fvisual stacked">
        {visual.bars.map((b, i) => <Bar key={i} {...b} />)}
        {visual.caption && <p className="fcaption">{visual.caption}</p>}
      </div>
    );
  }
  if (visual.kind === "equivalencia") {
    return (
      <div className="fvisual">
        <Bar num={visual.a} den={visual.b} label={`${visual.a}/${visual.b}`} />
        <Bar num={0} den={visual.target_den} label={`?/${visual.target_den}`} tone="soft" />
      </div>
    );
  }
  return (
    <div className="fvisual">
      <Bar num={visual.a} den={visual.b} label={`${visual.a}/${visual.b}`} />
      <span className="plus" aria-hidden="true">+</span>
      <Bar num={visual.c} den={visual.d} label={`${visual.c}/${visual.d}`} tone="b" />
    </div>
  );
}
