"use client";

import { useEffect, useRef } from "react";

export type VoiceOrbMode = "idle" | "interviewer" | "candidate" | "listening";

const LABELS: Record<VoiceOrbMode, string> = {
  idle: "Ready",
  interviewer: "Interviewer speaking",
  candidate: "Hearing you",
  listening: "Listening",
};

const NEUTRAL: [string, string, string, string, string] = ["#94a3b8", "#cbd5e1", "#e2e8f0", "#0b1220", "#64748b"];
const NEUTRAL_RIM =
  "conic-gradient(from 120deg, #94a3b8, #e2e8f0, #64748b, transparent 58%, #94a3b8)";

const PALETTES: Record<VoiceOrbMode, [string, string, string, string, string]> = {
  idle: NEUTRAL,
  listening: NEUTRAL,
  interviewer: ["#4ade80", "#2dd4bf", "#a3e635", "#04210f", "#86efac"],
  candidate: ["#fb7185", "#fb923c", "#f43f5e", "#2a0a0e", "#fda4af"],
};

const RIMS: Record<VoiceOrbMode, string> = {
  idle: NEUTRAL_RIM,
  listening: NEUTRAL_RIM,
  interviewer: "conic-gradient(from 120deg, #4ade80, #2dd4bf, #a3e635, #86efac, transparent 58%, #4ade80)",
  candidate: "conic-gradient(from 120deg, #fb7185, #fb923c, #f43f5e, #fda4af, transparent 58%, #fb7185)",
};

const BLOBS = [
  { x: 0.68, y: 0.22, z: 0.31, w: 0.62, r: 0.4 },
  { x: -0.52, y: 0.58, z: -0.18, w: 0.6, r: 0.34 },
  { x: 0.12, y: -0.64, z: 0.48, w: 0.58, r: 0.3 },
  { x: -0.28, y: -0.2, z: -0.72, w: 0.6, r: 0.26 },
  { x: 0.48, y: 0.42, z: -0.46, w: -0.62, r: 0.24 },
  { x: -0.62, y: 0.08, z: 0.36, w: -0.7, r: 0.22 },
  { x: 0.18, y: 0.7, z: 0.12, w: -0.68, r: 0.2 },
  { x: 0.36, y: -0.38, z: 0.64, w: 0.56, r: 0.18 },
  { x: -0.14, y: 0.16, z: -0.22, w: 0.95, r: 0.16 },
];

const PARTICLES = Array.from({ length: 26 }, (_, i) => {
  const a = (i / 26) * Math.PI * 2;
  const b = ((i * 11) % 26 / 26) * Math.PI;
  return {
    x: Math.cos(a) * Math.sin(b),
    y: Math.sin(a) * Math.sin(b),
    z: Math.cos(b),
    w: Math.sin(a * 1.8 + i * 0.31),
    s: 0.55 + (i % 6) * 0.12,
  };
});

export function voiceOrbMode(input: {
  interviewer: boolean;
  recording: boolean;
  candidateLevel: number;
}): VoiceOrbMode {
  if (input.interviewer) return "interviewer";
  if (input.recording && input.candidateLevel >= 0.018) return "candidate";
  if (input.recording) return "listening";
  return "idle";
}

function hexRgb(hex: string) {
  const value = hex.replace("#", "");
  return [
    Number.parseInt(value.slice(0, 2), 16),
    Number.parseInt(value.slice(2, 4), 16),
    Number.parseInt(value.slice(4, 6), 16),
  ] as const;
}

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t;
}

function rotate4d(x: number, y: number, z: number, w: number, t: number, spin: number) {
  const xw = t * (0.62 + spin * 0.35);
  const yz = t * (0.44 + spin * 0.22);
  const yw = t * (0.31 + spin * 0.18);
  const xy = t * (0.19 + spin * 0.12);
  const x1 = x * Math.cos(xw) - w * Math.sin(xw);
  const w1 = x * Math.sin(xw) + w * Math.cos(xw);
  const y1 = y * Math.cos(yz) - z * Math.sin(yz);
  const z1 = y * Math.sin(yz) + z * Math.cos(yz);
  const y2 = y1 * Math.cos(yw) - w1 * Math.sin(yw);
  const w2 = y1 * Math.sin(yw) + w1 * Math.cos(yw);
  const x2 = x1 * Math.cos(xy) - y2 * Math.sin(xy);
  const y3 = x1 * Math.sin(xy) + y2 * Math.cos(xy);
  const k = 2.05 / Math.max(1.15, 2.05 - w2);
  return { x: x2 * k, y: y3 * k, z: z1 * k, depth: 0.62 + (z1 + 1) * 0.22 };
}

function clampInside(x: number, y: number, limit: number) {
  const mag = Math.hypot(x, y);
  if (mag <= limit || mag === 0) return { x, y };
  const scale = limit / mag;
  return { x: x * scale, y: y * scale };
}

export function VoiceOrb({
  mode,
  level,
  status,
  size = "md",
}: {
  mode: VoiceOrbMode;
  level: number;
  status?: string;
  size?: "sm" | "md";
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const stateRef = useRef({ mode, level: 0.2 });
  const mixRef = useRef(PALETTES[mode].map((hex) => [...hexRgb(hex)]));
  stateRef.current = {
    mode,
    level:
      mode === "interviewer" || mode === "candidate"
        ? Math.max(0.52, level)
        : Math.max(0.28, Math.min(1, level)),
  };
  const box = size === "sm" ? 144 : 220;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = box * dpr;
    canvas.height = box * dpr;
    ctx.scale(dpr, dpr);

    let t = 0;
    let raf = 0;
    const draw = () => {
      const { mode: current, level: energy } = stateRef.current;
      const target = PALETTES[current].map((hex) => hexRgb(hex));
      mixRef.current = mixRef.current.map((rgb, i) => [
        lerp(rgb[0], target[i][0], 0.07),
        lerp(rgb[1], target[i][1], 0.07),
        lerp(rgb[2], target[i][2], 0.07),
      ]);
      const colors = mixRef.current;
      const mid = box / 2;
      const spin = current === "idle" ? 0.35 : current === "listening" ? 0.7 : 1;
      t += 0.012 + energy * 0.028 * spin;
      ctx.clearRect(0, 0, box, box);
      ctx.save();
      ctx.translate(mid, mid);
      ctx.scale(1 + Math.sin(t * 1.3) * 0.018 * (0.4 + energy), 1 + Math.cos(t * 1.1) * 0.018 * (0.4 + energy));
      ctx.translate(-mid, -mid);
      ctx.beginPath();
      ctx.arc(mid, mid, mid - 2, 0, Math.PI * 2);
      ctx.clip();

      const [br, bg, bb] = colors[3];
      ctx.fillStyle = `rgb(${Math.max(4, br)} ${Math.max(4, bg)} ${Math.max(4, bb)})`;
      ctx.fillRect(0, 0, box, box);

      const glowColors = [colors[0], colors[1], colors[2], colors[4]];
      const projected = BLOBS.map((blob, index) => {
        const p = rotate4d(blob.x, blob.y, blob.z, blob.w, t + index * 0.11, energy);
        const pos = clampInside(
          p.x * mid * (0.26 + energy * 0.18),
          p.y * mid * (0.26 + energy * 0.18),
          mid * 0.46,
        );
        return {
          x: mid + pos.x,
          y: mid + pos.y,
          r: box * blob.r * (1.05 + energy * 0.7) * p.depth,
          depth: p.depth,
          color: glowColors[index % glowColors.length],
        };
      });

      ctx.globalCompositeOperation = "lighter";
      projected.forEach((blob, index) => {
        const [r, g, b] = blob.color;
        const pulse = 0.88 + Math.sin(t * 2.1 + index) * 0.1;
        const gradient = ctx.createRadialGradient(blob.x, blob.y, blob.r * 0.02, blob.x, blob.y, blob.r);
        gradient.addColorStop(0, `rgba(${r},${g},${b},${0.86 * pulse})`);
        gradient.addColorStop(0.32, `rgba(${r},${g},${b},${0.42 * pulse})`);
        gradient.addColorStop(0.7, `rgba(${r},${g},${b},0.1)`);
        gradient.addColorStop(1, `rgba(${r},${g},${b},0)`);
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(blob.x, blob.y, blob.r, 0, Math.PI * 2);
        ctx.fill();
      });

      for (let i = 0; i < projected.length; i += 1) {
        for (let j = i + 1; j < projected.length; j += 1) {
          const a = projected[i];
          const b = projected[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const dist = Math.hypot(dx, dy);
          if (dist > box * 0.42 || dist < 8) continue;
          const [r, g, bl] = a.color;
          ctx.strokeStyle = `rgba(${r},${g},${bl},${0.16 + energy * 0.18})`;
          ctx.lineWidth = 1.6 + energy * 2;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.quadraticCurveTo(mid + Math.sin(t + i) * 8, mid + Math.cos(t + j) * 8, b.x, b.y);
          ctx.stroke();
        }
      }

      PARTICLES.forEach((particle, index) => {
        const p = rotate4d(particle.x, particle.y, particle.z, particle.w, t * particle.s + 1.7, energy);
        const pos = clampInside(p.x * mid * (0.38 + energy * 0.14), p.y * mid * (0.38 + energy * 0.14), mid * 0.62);
        const x = mid + pos.x;
        const y = mid + pos.y;
        const [r, g, b] = glowColors[index % glowColors.length];
        const radius = (1.05 + energy * 2.1) * p.depth;
        ctx.fillStyle = `rgba(${r},${g},${b},${0.35 + energy * 0.5})`;
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fill();
      });

      const [cr, cg, cb] = colors[1];
      const core = ctx.createRadialGradient(mid, mid, box * 0.01, mid, mid, box * (0.26 + energy * 0.1));
      core.addColorStop(0, `rgba(${cr},${cg},${cb},${0.55 + energy * 0.3})`);
      core.addColorStop(0.45, `rgba(${cr},${cg},${cb},0.18)`);
      core.addColorStop(1, `rgba(${cr},${cg},${cb},0)`);
      ctx.fillStyle = core;
      ctx.beginPath();
      ctx.arc(mid, mid, box * 0.34, 0, Math.PI * 2);
      ctx.fill();

      ctx.globalCompositeOperation = "source-over";
      const [er, eg, eb] = colors[0];
      const fresnel = ctx.createRadialGradient(mid, mid, mid * 0.55, mid, mid, mid);
      fresnel.addColorStop(0, "rgba(0,0,0,0)");
      fresnel.addColorStop(0.7, "rgba(0,0,0,0)");
      fresnel.addColorStop(0.88, `rgba(${er},${eg},${eb},0.28)`);
      fresnel.addColorStop(1, "rgba(255,255,255,0.16)");
      ctx.fillStyle = fresnel;
      ctx.fillRect(0, 0, box, box);

      for (let i = 0; i < 3; i += 1) {
        const [rr, gg, bb] = glowColors[i];
        ctx.strokeStyle = `rgba(${rr},${gg},${bb},${0.12 + energy * 0.14})`;
        ctx.lineWidth = 6 + energy * 4;
        ctx.beginPath();
        ctx.ellipse(
          mid + Math.cos(t * 0.8 + i) * 4,
          mid + Math.sin(t * 0.7 + i) * 4,
          mid * (0.58 + i * 0.08),
          mid * (0.36 + i * 0.05),
          t * (0.4 + i * 0.22),
          0,
          Math.PI * 2,
        );
        ctx.stroke();
      }

      const shade = ctx.createRadialGradient(mid * 0.68, mid * 0.56, box * 0.03, mid, mid, mid);
      shade.addColorStop(0, "rgba(255,255,255,0.1)");
      shade.addColorStop(0.42, "rgba(255,255,255,0)");
      shade.addColorStop(1, "rgba(0,0,0,0.18)");
      ctx.fillStyle = shade;
      ctx.fillRect(0, 0, box, box);
      ctx.restore();
      raf = window.requestAnimationFrame(draw);
    };
    raf = window.requestAnimationFrame(draw);
    return () => window.cancelAnimationFrame(raf);
  }, [box]);

  const energy = stateRef.current.level;
  const glow =
    mode === "interviewer"
      ? "rgba(74, 222, 128, 0.48)"
      : mode === "candidate"
        ? "rgba(251, 113, 133, 0.46)"
        : "rgba(148, 163, 184, 0.28)";

  return (
    <div className="grid justify-items-center gap-3">
      <div
        className="relative"
        style={{
          width: box,
          height: box,
          transform: `scale(${0.88 + energy * 0.24})`,
          transition: "transform 160ms ease",
        }}
        role="img"
        aria-label={LABELS[mode]}
      >
        <span
          className="pointer-events-none absolute -inset-12 rounded-full blur-3xl"
          style={{ background: glow, animation: "voice-orb-halo 2.8s ease-in-out infinite" }}
        />
        <span
          className="pointer-events-none absolute -inset-4 rounded-full"
          style={{
            border: "1px solid rgba(255,255,255,0.1)",
            boxShadow: `0 0 48px ${glow}`,
            animation: "voice-orb-ripple 2.6s ease-out infinite",
          }}
        />
        <span
          className="pointer-events-none absolute -inset-8 rounded-full"
          style={{
            border: "1px solid rgba(255,255,255,0.05)",
            animation: "voice-orb-ripple 2.6s ease-out 0.85s infinite",
          }}
        />
        <canvas ref={canvasRef} className="relative h-full w-full rounded-full" style={{ width: box, height: box }} />
        <span
          className="pointer-events-none absolute inset-0 rounded-full"
          style={{
            background:
              "radial-gradient(circle at 28% 20%, rgba(255,255,255,0.14), transparent 22%), radial-gradient(circle at 74% 78%, rgba(255,255,255,0.03), transparent 28%)",
            boxShadow: "inset 0 -18px 22px rgba(0,0,0,0.22), inset 0 10px 14px rgba(255,255,255,0.05)",
          }}
        />
        <span
          className="pointer-events-none absolute left-[16%] top-[12%] h-[13%] w-[22%] rounded-full bg-white/20 blur-[2px]"
          style={{ animation: "voice-orb-shimmer 3.2s ease-in-out infinite" }}
        />
        <span
          className="pointer-events-none absolute inset-0 rounded-full"
          style={{
            animation: "voice-orb-spin 14s linear infinite",
            background: RIMS[mode],
            WebkitMask: "radial-gradient(circle, transparent 61%, #000 64%, #000 70%, transparent 73%)",
            mask: "radial-gradient(circle, transparent 61%, #000 64%, #000 70%, transparent 73%)",
          }}
        />
        <span
          className="pointer-events-none absolute inset-0 rounded-full"
          style={{
            animation: "voice-orb-spin-reverse 22s linear infinite",
            background: RIMS[mode],
            opacity: 0.45,
            WebkitMask: "radial-gradient(circle, transparent 72%, #000 75%, #000 79%, transparent 82%)",
            mask: "radial-gradient(circle, transparent 72%, #000 75%, #000 79%, transparent 82%)",
          }}
        />
      </div>
      <p className="text-[0.95rem] font-medium">{LABELS[mode]}</p>
      {status ? <p className="max-w-xs text-center text-sm text-muted-foreground">{status}</p> : null}
    </div>
  );
}
