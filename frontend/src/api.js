// Cliente mínimo de la API. Las claves de IA viven solo en el backend.
// El token de sesión se guarda en este navegador (por comodidad: si se borra,
// basta con volver a entrar; el progreso real vive en el servidor).
const TOKEN_KEY = "thinkloop.token";

export const authToken = {
  get() { try { return localStorage.getItem(TOKEN_KEY) || ""; } catch { return ""; } },
  set(t) { try { localStorage.setItem(TOKEN_KEY, t); } catch { /* sin almacenamiento */ } },
  clear() { try { localStorage.removeItem(TOKEN_KEY); } catch { /* nada */ } },
};

async function request(method, path, body, extraHeaders) {
  const token = authToken.get();
  const headers = {
    ...(body ? { "Content-Type": "application/json" } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(extraHeaders || {}),
  };
  const res = await fetch(`/api${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401 && token && !path.startsWith("/auth/") && !path.startsWith("/teacher/")) {
      // La sesión expiró: la app regresa a la pantalla de entrada
      window.dispatchEvent(new Event("thinkloop:logout"));
    }
    const detail = Array.isArray(data.detail) ? "Revisa lo que escribiste." : data.detail;
    throw new Error(detail || "Algo falló. Intenta de nuevo.");
  }
  return data;
}

const pin = (p) => ({ "X-Teacher-Pin": p });

export const api = {
  health: () => request("GET", "/health"),
  styles: () => request("GET", "/tutor-styles"),
  // Cuenta (sin correo: usuario + contraseña + código de recuperación)
  register: (username, password, tutor_style, group_code) =>
    request("POST", "/auth/register", { username, password, tutor_style, group_code }),
  login: (username, password) => request("POST", "/auth/login", { username, password }),
  reset: (username, recovery_code, new_password) =>
    request("POST", "/auth/reset", { username, recovery_code, new_password }),
  logout: () => request("POST", "/auth/logout"),
  me: () => request("GET", "/me"),
  setStyle: (tutor_style) => request("PATCH", "/me", { tutor_style }),
  deleteMe: () => request("DELETE", "/me"),
  progress: () => request("GET", "/me/progress"),
  achievements: () => request("GET", "/me/achievements"),
  certificates: () => request("GET", "/me/certificates"),
  // Cursos y sesión de estudio
  courses: () => request("GET", "/courses"),
  startCourse: (courseId, days_away) =>
    request("POST", `/courses/${encodeURIComponent(courseId)}/session`, days_away != null ? { days_away } : {}),
  course: (courseId) => request("GET", `/courses/${encodeURIComponent(courseId)}`),
  theory: (sid, option) => request("POST", `/sessions/${sid}/theory`, { option }),
  check: (sid, option) => request("POST", `/sessions/${sid}/check`, { option }),
  examOption: (sid, option) => request("POST", `/sessions/${sid}/exam`, { option }),
  predict: (sid, choice) => request("POST", `/sessions/${sid}/predict`, { choice }),
  step: (sid, values) => request("POST", `/sessions/${sid}/step`, { values }),
  answer: (sid, answer) => request("POST", `/sessions/${sid}/answer`, { answer }),
  dontKnow: (sid) => request("POST", `/sessions/${sid}/answer`, { dont_know: true }),
  hint: (sid) => request("POST", `/sessions/${sid}/hint`),
  example: (sid) => request("POST", `/sessions/${sid}/example`),
  skip: (sid) => request("POST", `/sessions/${sid}/skip`),
  message: (sid, text) => request("POST", `/sessions/${sid}/message`, { text }),
  pause: (sid) => request("POST", `/sessions/${sid}/pause`),
  // Panel docente (el PIN viaja en un encabezado, no en la URL)
  teacherGroups: (p) => request("GET", "/teacher/groups", null, pin(p)),
  teacherCourses: (p) => request("GET", "/teacher/courses", null, pin(p)),
  teacherGroup: (p, code, course) =>
    request("GET", `/teacher/groups/${encodeURIComponent(code)}?course=${encodeURIComponent(course || "MAT-FRAC")}`,
            null, pin(p)),
  teacherDemo: (p) => request("POST", "/teacher/demo-group", null, pin(p)),
};
