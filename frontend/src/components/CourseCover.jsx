// Portadas generadas con una plantilla SVG propia (sin imágenes con derechos de autor):
// un color por curso, figuras suaves de fondo y el símbolo matemático del curso.
export const TONES = {
  naranja: { bg: "#f97316", soft: "#fed7aa" },
  verde: { bg: "#0d9488", soft: "#99f6e4" },
  amarillo: { bg: "#ca8a04", soft: "#fde68a" },
  rosa: { bg: "#db2777", soft: "#fbcfe8" },
  morado: { bg: "#7c3aed", soft: "#ddd6fe" },
  azul: { bg: "#2563eb", soft: "#bfdbfe" },
};

export default function CourseCover({ cover, size = "md", title }) {
  const tone = TONES[cover?.tono] || TONES.naranja;
  const symbol = cover?.simbolo || "∞";
  const small = size === "sm";
  return (
    <svg className={`cover cover-${size}`} viewBox="0 0 160 96" role="img"
         aria-label={title ? `Portada del curso ${title}` : undefined} aria-hidden={title ? undefined : true}
         preserveAspectRatio="xMidYMid slice">
      <rect width="160" height="96" fill={tone.bg} />
      <circle cx="18" cy="84" r="34" fill={tone.soft} opacity="0.35" />
      <circle cx="146" cy="10" r="26" fill={tone.soft} opacity="0.3" />
      {!small && (
        <g fill="#fff" opacity="0.18">
          {[0, 1, 2, 3, 4].map((i) => <circle key={i} cx={102 + i * 11} cy="80" r="3" />)}
        </g>
      )}
      {/* Una letra (la x del álgebra) va en cursiva con serifa para no confundirse con «×» */}
      <text x="80" y="50" textAnchor="middle" dominantBaseline="central" fill="#fff"
            fontFamily={/^[a-z]$/i.test(symbol) ? "Georgia, 'Times New Roman', serif" : "'Nunito Variable', system-ui, sans-serif"}
            fontStyle={/^[a-z]$/i.test(symbol) ? "italic" : "normal"} fontWeight="900"
            fontSize={symbol.length > 1 ? 40 : 58}>{symbol}</text>
    </svg>
  );
}
