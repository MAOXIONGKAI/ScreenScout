"use client";

import { useEffect, useRef } from "react";

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  baseVx: number;
  baseVy: number;
  radius: number;
  color: string;
  baseAlpha: number;
  currentAlpha: number;
  pulseSpeed: number;
  pulseOffset: number;
}

const PARTICLE_COLORS = [
  "rgba(192, 132, 252", // Light Purple (Purple-400)
  "rgba(216, 180, 254", // Soft Lavender (Purple-300)
  "rgba(168, 85, 247", // Vibrant Light Purple (Purple-500)
  "rgba(233, 213, 255", // Bright Lavender (Purple-200)
  "rgba(175, 120, 245", // Lavender Purple
];

export default function ParticleBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const mouse = {
      x: -1000,
      y: -1000,
      radius: 140,
      active: false,
    };

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
      initParticles();
    };

    const handleMouseMove = (e: MouseEvent) => {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
      mouse.active = true;
    };

    const handleMouseLeave = () => {
      mouse.active = false;
      mouse.x = -1000;
      mouse.y = -1000;
    };

    window.addEventListener("resize", handleResize);
    window.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseleave", handleMouseLeave);

    let particles: Particle[] = [];

    const initParticles = () => {
      // Ultra-dense particle count
      const count = Math.min(
        550,
        Math.max(200, Math.floor((width * height) / 2600))
      );
      particles = [];

      for (let i = 0; i < count; i++) {
        const color =
          PARTICLE_COLORS[Math.floor(Math.random() * PARTICLE_COLORS.length)];
        const baseAlpha = 0.2 + Math.random() * 0.55;
        const baseVx = (Math.random() - 0.5) * 0.35;
        const baseVy = (Math.random() - 0.5) * 0.35;

        particles.push({
          x: Math.random() * width,
          y: Math.random() * height,
          vx: 0,
          vy: 0,
          baseVx,
          baseVy,
          radius: 1.0 + Math.random() * 1.8,
          color,
          baseAlpha,
          currentAlpha: baseAlpha,
          pulseSpeed: 0.015 + Math.random() * 0.025,
          pulseOffset: Math.random() * Math.PI * 2,
        });
      }
    };

    initParticles();

    let frame = 0;
    const render = () => {
      frame++;
      ctx.clearRect(0, 0, width, height);

      // Update & draw particles
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];

        // Pulsing glow
        const pulse = Math.sin(frame * p.pulseSpeed + p.pulseOffset);
        p.currentAlpha = p.baseAlpha + pulse * 0.15;

        // Mouse hover dispersion effect
        if (mouse.active) {
          const dx = p.x - mouse.x;
          const dy = p.y - mouse.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < mouse.radius && dist > 0) {
            // Calculate force inverse to distance
            const force = (1 - dist / mouse.radius) * 8.0;
            const angle = Math.atan2(dy, dx);
            const fx = Math.cos(angle) * force;
            const fy = Math.sin(angle) * force;

            p.vx += fx * 0.55;
            p.vy += fy * 0.55;

            // Brighten particle near cursor
            p.currentAlpha = Math.min(1, p.currentAlpha + (1 - dist / mouse.radius) * 0.6);
          }
        }

        // Apply friction and ambient drift
        p.vx *= 0.91;
        p.vy *= 0.91;
        p.x += p.baseVx + p.vx;
        p.y += p.baseVy + p.vy;

        // Screen wrap-around
        if (p.x < -20) p.x = width + 20;
        if (p.x > width + 20) p.x = -20;
        if (p.y < -20) p.y = height + 20;
        if (p.y > height + 20) p.y = -20;

        // Draw particle with light purple glow
        ctx.save();
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = `${p.color}, ${p.currentAlpha})`;
        ctx.shadowBlur = 6;
        ctx.shadowColor = `${p.color}, 0.5)`;
        ctx.fill();
        ctx.restore();

        // Constellation lines between close particles
        for (let j = i + 1; j < particles.length; j++) {
          const p2 = particles[j];
          const distx = p.x - p2.x;
          const disty = p.y - p2.y;
          const dist = Math.sqrt(distx * distx + disty * disty);

          if (dist < 52) {
            const lineAlpha = (1 - dist / 52) * 0.1;
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.strokeStyle = `rgba(192, 132, 252, ${lineAlpha})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseleave", handleMouseLeave);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
        pointerEvents: "none",
        zIndex: 0,
      }}
      aria-hidden="true"
    />
  );
}
