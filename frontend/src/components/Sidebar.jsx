// Menú lateral (en celular se vuelve una barra inferior de pestañas).
const ITEMS = [
  { page: "cursos", href: "#/cursos", label: "Cursos", icon: "M4 5h7v14H4zM13 5h7v14h-7z" },
  { page: "progreso", href: "#/progreso", label: "Progreso", icon: "M4 19V11M10 19V5M16 19v-6M22 19H2" },
  { page: "logros", href: "#/logros", label: "Logros", icon: "M12 3l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.4 6.8 19.1l1-5.8L3.5 9.2l5.9-.9z" },
  { page: "reconocimientos", href: "#/reconocimientos", label: "Reconocimientos",
    icon: "M5 4h14v11H5zM9 15l-1 6 4-2 4 2-1-6" },
];

export default function Sidebar({ page }) {
  const active = page === "curso" ? "cursos" : page === "constancia" ? "reconocimientos" : page;
  return (
    <nav className="sidebar" aria-label="Secciones">
      <ul>
        {ITEMS.map((it) => (
          <li key={it.page}>
            <a href={it.href} className={active === it.page ? "active" : ""}
               aria-current={active === it.page ? "page" : undefined}>
              <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" fill="none"
                   stroke="currentColor" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round">
                <path d={it.icon} />
              </svg>
              <span>{it.label}</span>
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
