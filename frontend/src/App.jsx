import { useCallback, useEffect, useState } from "react";
import { api, authToken } from "./api.js";
import AuthScreen from "./components/AuthScreen.jsx";
import AvatarMenu from "./components/AvatarMenu.jsx";
import Sidebar from "./components/Sidebar.jsx";
import CoursesPage from "./components/CoursesPage.jsx";
import LessonPage from "./components/LessonPage.jsx";
import ProgressPage from "./components/ProgressPage.jsx";
import AchievementsPage from "./components/AchievementsPage.jsx";
import CertificatesPage, { CertificateView } from "./components/CertificatesPage.jsx";
import TeacherDashboard from "./components/TeacherDashboard.jsx";

// Rutas mínimas con el hash, sin librerías: #/cursos, #/curso/MAT-SUMA, #/progreso,
// #/logros, #/reconocimientos, #/constancia/MAT-SUMA y #docente.
function parseRoute(hash) {
  if (hash === "#docente") return { page: "docente" };
  const [, page = "cursos", arg] = (hash || "").replace(/^#\/?/, "/").split("/");
  return { page: page || "cursos", arg: arg ? decodeURIComponent(arg) : undefined };
}

function useRoute() {
  const [route, setRoute] = useState(() => parseRoute(window.location.hash));
  useEffect(() => {
    const on = () => setRoute(parseRoute(window.location.hash));
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return route;
}

export default function App() {
  const [student, setStudent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [aiProvider, setAiProvider] = useState("");
  const route = useRoute();

  const logoutLocal = useCallback(() => {
    authToken.clear();
    setStudent(null);
  }, []);

  useEffect(() => {
    api.health().then((h) => setAiProvider(h.ai_provider)).catch(() => {});
    window.addEventListener("thinkloop:logout", logoutLocal);
    if (!authToken.get()) { setLoading(false); }
    else {
      api.me().then(setStudent).catch(logoutLocal).finally(() => setLoading(false));
    }
    return () => window.removeEventListener("thinkloop:logout", logoutLocal);
  }, [logoutLocal]);

  function handleAuth({ token, student: s }) {
    authToken.set(token);
    setStudent(s);
    if (!window.location.hash || window.location.hash === "#docente") window.location.hash = "#/cursos";
  }

  async function handleLogout() {
    try { await api.logout(); } catch { /* aunque falle, salimos */ }
    logoutLocal();
  }

  async function handleDelete() {
    if (!window.confirm("¿Borrar tu cuenta, tu progreso y todos tus datos? Esto no se puede deshacer.")) return;
    await api.deleteMe();
    logoutLocal();
  }

  const teacherMode = route.page === "docente";
  const printView = route.page === "constancia";

  return (
    <div className={`app ${printView ? "print-mode" : ""}`}>
      {/* No usa href="#…": el hash ya se usa para las rutas */}
      <a className="skip-link" href="#/" onClick={(e) => {
        e.preventDefault();
        document.getElementById("contenido-principal")?.focus();
      }}>Saltar al contenido</a>
      <header className="topbar">
        <a className="brand" href="#/cursos" aria-label="ThinkLoop, ir a cursos">
          <span className="logo" aria-hidden="true">∞</span>
          <span>ThinkLoop</span>
        </a>
        {teacherMode ? (
          <nav className="topbar-actions" aria-label="Docente">
            <span className="hello">Panel docente</span>
            <a className="link light" href="#/cursos">Volver</a>
          </nav>
        ) : student && (
          <AvatarMenu student={student} onStudent={setStudent} onLogout={handleLogout} onDelete={handleDelete} />
        )}
      </header>

      {teacherMode ? (
        <main id="contenido-principal" className="page" tabIndex={-1}><TeacherDashboard /></main>
      ) : loading ? (
        <main className="page"><p className="center muted">Cargando…</p></main>
      ) : !student ? (
        <main id="contenido-principal" className="page" tabIndex={-1}><AuthScreen onAuth={handleAuth} /></main>
      ) : (
        <div className={`shell ${route.page === "curso" ? "focus" : ""}`}>
          {/* Dentro de una lección el menú se oculta para dejarle todo el espacio */}
          {route.page !== "curso" && <Sidebar page={route.page} />}
          <main id="contenido-principal" className="page" tabIndex={-1}>
            <Page route={route} student={student} setStudent={setStudent} />
          </main>
        </div>
      )}

      <footer className="footer muted">
        Prototipo de hackathon · Las respuestas las revisa el sistema, no la IA
        {aiProvider && ` · IA: ${aiProvider === "mock" ? "modo demo (sin IA)" : aiProvider}`}
        {!teacherMode && <> · <a className="link" href="#docente">Soy docente</a></>}
      </footer>
    </div>
  );
}

function Page({ route, student, setStudent }) {
  switch (route.page) {
    case "curso":
      return <LessonPage key={route.arg} courseId={route.arg} student={student} setStudent={setStudent} />;
    case "progreso":
      return <ProgressPage />;
    case "logros":
      return <AchievementsPage />;
    case "reconocimientos":
      return <CertificatesPage />;
    case "constancia":
      return <CertificateView courseId={route.arg} />;
    default:
      return <CoursesPage student={student} />;
  }
}
