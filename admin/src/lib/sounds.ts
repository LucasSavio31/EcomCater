'use client';

/** Efeitos sonoros do painel (venda paga / devolução entregue), sintetizados
 * via Web Audio API -- sem arquivo de áudio externo para carregar/manter. */

let ctx: AudioContext | null = null;

function getCtx(): AudioContext | null {
  if (typeof window === 'undefined') return null;
  const Ctor = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!Ctor) return null;
  if (!ctx) ctx = new Ctor();
  if (ctx.state === 'suspended') void ctx.resume().catch(() => {});
  return ctx;
}

function tone(
  ac: AudioContext,
  freq: number,
  start: number,
  duration: number,
  opts: { type?: OscillatorType; gain?: number; freqEnd?: number } = {},
): void {
  const osc = ac.createOscillator();
  const gain = ac.createGain();
  osc.type = opts.type ?? 'sine';
  const t0 = ac.currentTime + start;
  osc.frequency.setValueAtTime(freq, t0);
  if (opts.freqEnd !== undefined) {
    osc.frequency.exponentialRampToValueAtTime(Math.max(opts.freqEnd, 1), t0 + duration);
  }
  const peak = opts.gain ?? 0.2;
  gain.gain.setValueAtTime(0.0001, t0);
  gain.gain.exponentialRampToValueAtTime(peak, t0 + 0.01);
  gain.gain.exponentialRampToValueAtTime(0.0001, t0 + duration);
  osc.connect(gain);
  gain.connect(ac.destination);
  osc.start(t0);
  osc.stop(t0 + duration + 0.02);
}

/** Som de caixa registradora ("cha-ching") -- duas notas metálicas rápidas. */
export function playSaleSound(): void {
  const ac = getCtx();
  if (!ac) return;
  tone(ac, 1567.98, 0, 0.12, { type: 'square', gain: 0.15 });
  tone(ac, 2093.0, 0.09, 0.3, { type: 'square', gain: 0.18 });
  tone(ac, 2637.02, 0.09, 0.3, { type: 'square', gain: 0.1 });
}

/** Som de "glup" (engolir) -- glide de pitch descendente. */
export function playReturnSound(): void {
  const ac = getCtx();
  if (!ac) return;
  tone(ac, 420, 0, 0.24, { type: 'sine', freqEnd: 140, gain: 0.22 });
}
