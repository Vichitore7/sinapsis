// Dibujos para la teoría y las lecciones (SVG ligero, sin imágenes externas).
// Fracciones -> FractionVisual. Lo demás: bloques de base 10, columnas, arreglos,
// reparto, cuadrícula, balanza y el modelo de barras del método Singapur.
import FractionVisual from "./FractionVisual.jsx";

const INK = "var(--text)";

function Base10({ numero }) {
  const c = Math.floor(numero / 100), d = Math.floor((numero % 100) / 10), u = numero % 10;
  const cols = [
    ...(c ? [{ name: "Centenas", n: c, value: c * 100, draw: (i) => <Hundred key={i} /> }] : []),
    { name: "Decenas", n: d, value: d * 10, draw: (i) => <Ten key={i} /> },
    { name: "Unidades", n: u, value: u, draw: (i) => <One key={i} /> },
  ];
  return (
    <div className="b10" role="img" aria-label={`${numero}: ${cols.map((x) => `${x.n} ${x.name.toLowerCase()}`).join(", ")}`}>
      {cols.map((col) => (
        <div key={col.name} className="b10-col">
          <span className="b10-head">{col.name}</span>
          <div className="b10-blocks">{Array.from({ length: col.n }).map((_, i) => col.draw(i))}</div>
          <span className="b10-digit">{col.n}</span>
          <span className="b10-value">= {col.value}</span>
        </div>
      ))}
    </div>
  );
}
const Hundred = () => (
  <svg viewBox="0 0 40 40" width="40" height="40" aria-hidden="true">
    <rect x="0.5" y="0.5" width="39" height="39" fill="var(--orange)" stroke="var(--orange-dark)" />
    {Array.from({ length: 9 }).map((_, i) => (
      <g key={i} stroke="#fff" strokeWidth="0.6" opacity="0.7">
        <line x1={(i + 1) * 4} y1="0" x2={(i + 1) * 4} y2="40" />
        <line x1="0" y1={(i + 1) * 4} x2="40" y2={(i + 1) * 4} />
      </g>
    ))}
  </svg>
);
const Ten = () => (
  <svg viewBox="0 0 6 40" width="6" height="40" aria-hidden="true">
    <rect x="0.5" y="0.5" width="5" height="39" fill="var(--teal)" stroke="var(--teal)" />
    {Array.from({ length: 9 }).map((_, i) => <line key={i} x1="0" y1={(i + 1) * 4} x2="6" y2={(i + 1) * 4} stroke="#fff" strokeWidth="0.6" />)}
  </svg>
);
const One = () => (
  <svg viewBox="0 0 6 6" width="8" height="8" aria-hidden="true"><rect x="0.5" y="0.5" width="5" height="5" fill="var(--warn)" /></svg>
);

function Columns({ encabezados, filas }) {
  return (
    <table className="cols" aria-label="Operación por columnas">
      <thead><tr><th />{encabezados.map((h, i) => <th key={i} scope="col">{h}</th>)}</tr></thead>
      <tbody>
        {filas.map((r, i) => (
          <tr key={i} className={r.tipo || ""}>
            <th scope="row">{r.etiqueta}</th>
            {r.celdas.map((c, j) => <td key={j}>{c}</td>)}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Array2D({ filas, columnas }) {
  const s = 18;
  return (
    <svg viewBox={`0 0 ${columnas * s} ${filas * s}`} width={columnas * s * 1.4} role="img"
         aria-label={`${filas} filas de ${columnas}`}>
      {Array.from({ length: filas * columnas }).map((_, i) => (
        <circle key={i} cx={(i % columnas) * s + s / 2} cy={Math.floor(i / columnas) * s + s / 2} r={s / 3}
                fill={Math.floor(i / columnas) % 2 ? "var(--teal)" : "var(--orange)"} />
      ))}
    </svg>
  );
}

function Share({ total, grupos }) {
  const q = Math.floor(total / grupos), r = total % grupos;
  return (
    <div className="share" role="img" aria-label={`${total} repartidos entre ${grupos}: ${q} a cada uno, sobran ${r}`}>
      {Array.from({ length: grupos }).map((_, g) => (
        <div key={g} className="share-group">
          {Array.from({ length: q }).map((_, i) => <span key={i} className="dot" />)}
        </div>
      ))}
      {r > 0 && (
        <div className="share-left">
          {Array.from({ length: r }).map((_, i) => <span key={i} className="dot warn" />)}
          <span className="small">sobran</span>
        </div>
      )}
    </div>
  );
}

function Grid({ lado }) {
  const s = 20;
  return (
    <svg viewBox={`-14 -4 ${lado * s + 18} ${lado * s + 22}`} width={Math.min(220, lado * s + 40)} role="img"
         aria-label={`Cuadrado de ${lado} por lado`}>
      {Array.from({ length: lado * lado }).map((_, i) => (
        <rect key={i} x={(i % lado) * s} y={Math.floor(i / lado) * s} width={s} height={s}
              fill="var(--orange-soft)" stroke="var(--orange-dark)" strokeWidth="1" />
      ))}
      <text x={(lado * s) / 2} y={lado * s + 15} textAnchor="middle" fontSize="12" fill={INK}>{lado}</text>
      <text x="-9" y={(lado * s) / 2 + 4} textAnchor="middle" fontSize="12" fill={INK}>{lado}</text>
    </svg>
  );
}

function Scale({ izquierda, derecha }) {
  // Balanza: cada lado es un platillo con una «pesa» que lleva su texto
  const side = (x, label) => (
    <g key={x}>
      <line x1={x} y1="34" x2={x} y2="58" stroke={INK} strokeWidth="2" />
      <rect x={x - 42} y="58" width="84" height="30" rx="8" fill="var(--orange-bg)" stroke="var(--orange)" strokeWidth="2" />
      <text x={x} y="79" textAnchor="middle" fontSize="18" fontWeight="800" fill={INK}>{label}</text>
      <path d={`M${x - 50} 92 h100`} stroke="var(--orange-dark)" strokeWidth="4" strokeLinecap="round" />
    </g>
  );
  return (
    <svg viewBox="0 0 260 130" width="270" role="img" aria-label={`Balanza en equilibrio: ${izquierda} pesa lo mismo que ${derecha}`}>
      <polygon points="130,34 114,126 146,126" fill="var(--muted)" />
      <line x1="50" y1="34" x2="210" y2="34" stroke={INK} strokeWidth="4" strokeLinecap="round" />
      <circle cx="130" cy="34" r="5" fill={INK} />
      {side(50, izquierda)}
      {side(210, derecha)}
    </svg>
  );
}

// Modelo de barras (método Singapur): cada fila es una barra partida en segmentos
// proporcionales; los huecos (línea punteada) son lo que no se conoce, y la llave de
// abajo dice cuánto vale la barra completa. El servidor manda solo proporciones
// aproximadas (`peso`), nunca los tamaños exactos.
function BarModel({ filas }) {
  const describe = (f) =>
    `${f.etiqueta ? `${f.etiqueta}: ` : ""}${f.segmentos.map((s) => s.texto || "?").join(" + ")}` +
    (f.llave ? ` = ${f.llave}` : "");
  return (
    <div className="bmodel" role="img" aria-label={`Modelo de barras. ${filas.map(describe).join(". ")}`}>
      {filas.map((f, i) => (
        <div key={i} className="bm-row">
          {filas.some((x) => x.etiqueta) && <span className="bm-label">{f.etiqueta}</span>}
          <div className="bm-track">
            <div className="bm-bar" style={{ width: `${f.ancho}%` }}>
              <div className="bm-segs">
                {f.segmentos.map((s, j) => (
                  <span key={j} className={`bm-seg tone-${s.tono || "a"} ${s.hueco ? "hole" : ""}`}
                        style={{ flexGrow: s.peso }}>{s.texto}</span>
                ))}
              </div>
              {f.llave && (
                <div className="bm-brace" aria-hidden="true">
                  <span className="bm-brace-line" />
                  <span className="bm-brace-label">{f.llave}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function MathVisual({ visual }) {
  if (!visual) return null;
  const body = {
    base10: () => <Base10 {...visual} />,
    columnas: () => <Columns {...visual} />,
    arreglo: () => <Array2D {...visual} />,
    reparto: () => <Share {...visual} />,
    cuadricula: () => <Grid {...visual} />,
    balanza: () => <Scale {...visual} />,
    modelo: () => <BarModel {...visual} />,
  }[visual.kind];
  if (!body) return <FractionVisual visual={visual} />;
  return (
    <figure className="mvisual">
      {body()}
      {visual.caption && <figcaption className="fcaption">{visual.caption}</figcaption>}
    </figure>
  );
}
