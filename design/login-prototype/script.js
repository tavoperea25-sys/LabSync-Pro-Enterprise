// =============================================
// script.js — Login Plataforma HVE
// Gobernación del Cesar
// Animaciones con Motion (https://motion.dev)
// =============================================

import { animate, stagger } from 'https://cdn.jsdelivr.net/npm/motion@12.43.0/+esm';

const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

const ERROR_ICON = `
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <circle cx="12" cy="12" r="10"/>
    <line x1="12" y1="8" x2="12" y2="12"/>
    <line x1="12" y1="16" x2="12.01" y2="16"/>
  </svg>`;

/** Toggle mostrar / ocultar contraseña */
function togglePass() {
  const input = document.getElementById('password');
  const icon  = document.getElementById('eyeIcon');
  const btn   = document.getElementById('eyeBtn');

  const showing = input.type === 'password';
  input.type = showing ? 'text' : 'password';
  btn.setAttribute('aria-pressed', String(showing));
  btn.setAttribute('aria-label', showing ? 'Ocultar contraseña' : 'Mostrar contraseña');

  icon.innerHTML = showing
    ? `<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>`
    : `<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8
               a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4
               c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
       <line x1="1" y1="1" x2="23" y2="23"/>`;

  if (!reduceMotion) {
    animate(icon, { scale: [0.7, 1] }, { duration: 0.28, easing: [0.16, 1, 0.3, 1] });
  }
}

function mostrarError(id, msg) {
  const campo = document.getElementById(id);
  const errorEl = document.getElementById(`${id}-error`);

  campo.setAttribute('aria-invalid', 'true');
  errorEl.innerHTML = `${ERROR_ICON}<span>${msg}</span>`;

  if (!reduceMotion) {
    animate(campo.closest('.inp-wrap'), { x: [0, -6, 6, -4, 4, 0] }, { duration: 0.4, easing: 'ease-in-out' });
    animate(errorEl, { opacity: [0, 1], y: [-4, 0] }, { duration: 0.25, easing: [0.16, 1, 0.3, 1] });
  }
  return campo;
}

function limpiarErrores() {
  document.querySelectorAll('.err-msg').forEach(e => { e.innerHTML = ''; });
  document.querySelectorAll('input, select').forEach(el => el.removeAttribute('aria-invalid'));
}

function setCargando(cargando) {
  const btn = document.getElementById('loginBtn');
  btn.dataset.loading = String(cargando);
  btn.disabled = cargando;
}

/** Validación y envío */
function iniciarSesion(evt) {
  evt.preventDefault();

  const usuario  = document.getElementById('usuario').value.trim();
  const password = document.getElementById('password').value.trim();
  const area     = document.getElementById('area').value;
  const status   = document.getElementById('formStatus');

  limpiarErrores();
  status.textContent = '';

  const validaciones = [
    [!usuario,  'usuario',  'Por favor ingresa tu usuario.'],
    [!password, 'password', 'Por favor ingresa tu contraseña.'],
    [!area,     'area',     'Por favor selecciona tu área.'],
  ];

  let primerCampoInvalido = null;
  validaciones.forEach(([esInvalido, id, msg]) => {
    if (!esInvalido) return;
    const campo = mostrarError(id, msg);
    primerCampoInvalido ??= campo;
  });

  if (primerCampoInvalido) { primerCampoInvalido.focus(); return; }

  setCargando(true);

  // ── Conectar al backend aquí ──────────────────
  // fetch('/api/login', {
  //   method: 'POST',
  //   headers: { 'Content-Type': 'application/json' },
  //   body: JSON.stringify({ usuario, password, area })
  // })
  // .then(r => r.json())
  // .then(d => { if (d.success) window.location.href = '/dashboard'; })
  // .catch(console.error);
  // ─────────────────────────────────────────────

  window.setTimeout(() => {
    setCargando(false);
    status.textContent = `Bienvenido, ${usuario}. Área: ${area}.`;
  }, 900);
}

/** Efecto ripple en el botón principal */
function crearRipple(evt) {
  if (reduceMotion) return;
  const btn = evt.currentTarget;
  const rect = btn.getBoundingClientRect();
  const size = Math.max(rect.width, rect.height) * 1.6;
  const ripple = document.createElement('span');
  ripple.className = 'ripple';
  ripple.style.width = ripple.style.height = `${size}px`;
  ripple.style.left = `${(evt.clientX ?? rect.left + rect.width / 2) - rect.left - size / 2}px`;
  ripple.style.top  = `${(evt.clientY ?? rect.top + rect.height / 2) - rect.top - size / 2}px`;
  btn.appendChild(ripple);
  ripple.addEventListener('animationend', () => ripple.remove());
}

/** Entrada escalonada de los elementos marcados con [data-reveal] */
function animarEntrada() {
  const elementos = document.querySelectorAll('[data-reveal]');
  if (reduceMotion || !elementos.length) return;

  animate(
    elementos,
    { opacity: [0, 1], y: [14, 0] },
    { duration: 0.5, delay: stagger(0.05, { startDelay: 0.1 }), easing: [0.16, 1, 0.3, 1] }
  );
}

/** Micro-interacciones de hover / presión en elementos interactivos */
function vincularMicroanimaciones() {
  if (reduceMotion) return;

  const btn = document.getElementById('loginBtn');
  if (btn) {
    btn.addEventListener('mouseenter', () => animate(btn, { scale: 1.015, y: -2 }, { duration: 0.25, easing: 'ease-out' }));
    btn.addEventListener('mouseleave', () => animate(btn, { scale: 1, y: 0 }, { duration: 0.25, easing: 'ease-out' }));
    btn.addEventListener('mousedown',  () => animate(btn, { scale: 0.98 }, { duration: 0.12, easing: 'ease-out' }));
    btn.addEventListener('mouseup',    () => animate(btn, { scale: 1.015, y: -2 }, { duration: 0.18, easing: 'ease-out' }));
  }

  document.querySelectorAll('input, select').forEach(el => {
    const icon = el.closest('.inp-wrap')?.querySelector('.ico');
    if (!icon) return;
    el.addEventListener('focus', () => animate(icon, { scale: [1, 1.15, 1] }, { duration: 0.3, easing: [0.16, 1, 0.3, 1] }));
  });
}

function mostrarAyudaRecuperacion() {
  const hint = document.getElementById('forgotHint');
  hint.textContent = 'Contacta al administrador del sistema para restablecer tu contraseña.';
}

document.addEventListener('DOMContentLoaded', () => {
  animarEntrada();
  vincularMicroanimaciones();

  document.getElementById('eyeBtn')?.addEventListener('click', togglePass);
  document.getElementById('loginForm')?.addEventListener('submit', iniciarSesion);
  document.getElementById('loginBtn')?.addEventListener('click', crearRipple);
  document.getElementById('forgotBtn')?.addEventListener('click', mostrarAyudaRecuperacion);

  ['usuario', 'password', 'area'].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('input',  limpiarErrores);
      el.addEventListener('change', limpiarErrores);
    }
  });
});
