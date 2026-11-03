/* The air around the face: drifting ash and rising embers.
 *
 * Two populations on one canvas - dim motes that fall slowly and glowing
 * sparks that rise - with a little parallax against the pointer so the room
 * feels deeper than the page.
 */
(function () {
  class Mist {
    constructor(canvas) {
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.ash = [];
      this.embers = [];
      this.pointer = { x: 0, y: 0 };
      this.last = performance.now();
      this.resize();
      window.addEventListener("resize", () => this.resize());
      requestAnimationFrame((ts) => this.loop(ts));
    }

    resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      this.w = window.innerWidth;
      this.h = window.innerHeight;
      this.canvas.width = Math.round(this.w * dpr);
      this.canvas.height = Math.round(this.h * dpr);
      this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      this.spawn();
    }

    spawn() {
      const { w, h } = this;
      this.ash = Array.from({ length: Math.round((w * h) / 14000) }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        vy: 6 + Math.random() * 16,
        vx: (Math.random() - 0.5) * 5,
        size: Math.random() < 0.85 ? 1 : 1.6,
        alpha: 0.06 + Math.random() * 0.2,
      }));
      this.embers = Array.from({ length: Math.round((w * h) / 52000) }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        vy: -(8 + Math.random() * 26),
        vx: (Math.random() - 0.5) * 10,
        size: 0.8 + Math.random() * 1.9,
        alpha: 0.25 + Math.random() * 0.5,
        phase: Math.random() * Math.PI * 2,
      }));
    }

    setPointer(x, y) {
      this.pointer.x = x;
      this.pointer.y = y;
    }

    loop(ts) {
      const dt = Math.min(0.05, (ts - this.last) / 1000 || 0.016);
      this.last = ts;
      const ctx = this.ctx;
      const { w, h } = this;

      ctx.clearRect(0, 0, w, h);

      const shiftX = this.pointer.x * 12;
      const shiftY = this.pointer.y * 8;

      ctx.fillStyle = "rgba(196, 190, 176, 1)";
      for (const p of this.ash) {
        p.y += p.vy * dt;
        p.x += (p.vx + Math.sin((p.y + ts * 0.0004) * 0.01) * 4) * dt;
        if (p.y > h + 4) { p.y = -4; p.x = Math.random() * w; }
        if (p.x < -4) p.x = w + 4;
        if (p.x > w + 4) p.x = -4;
        ctx.globalAlpha = p.alpha;
        ctx.fillRect(p.x + shiftX * 0.3, p.y + shiftY * 0.3, p.size, p.size);
      }

      ctx.globalCompositeOperation = "lighter";
      for (const p of this.embers) {
        p.y += p.vy * dt;
        p.x += (p.vx + Math.sin(ts * 0.001 + p.phase) * 7) * dt;
        if (p.y < -6) { p.y = h + 6; p.x = Math.random() * w; p.phase = Math.random() * 6.28; }
        if (p.x < -6) p.x = w + 6;
        if (p.x > w + 6) p.x = -6;
        const flicker = 0.6 + 0.4 * Math.sin(ts * 0.004 + p.phase);
        const x = p.x + shiftX;
        const y = p.y + shiftY;
        const grd = ctx.createRadialGradient(x, y, 0, x, y, p.size * 6);
        grd.addColorStop(0, `rgba(255, 90, 60, ${(p.alpha * flicker).toFixed(3)})`);
        grd.addColorStop(0.4, `rgba(200, 32, 26, ${(p.alpha * flicker * 0.4).toFixed(3)})`);
        grd.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = grd;
        ctx.beginPath();
        ctx.arc(x, y, p.size * 6, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalCompositeOperation = "source-over";
      ctx.globalAlpha = 1;

      requestAnimationFrame((next) => this.loop(next));
    }
  }

  window.Mist = Mist;
})();
