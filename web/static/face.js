/* The eyes: two burning sockets on a canvas, and nothing else.
 *
 * Each socket is a tilted almond described as a field, sampled onto a monospace
 * grid so the portrait is really text. The interior is near-black, the rim and
 * the iris burn, and a slit pupil follows the pointer. The pair flares with his
 * voice, closes when he blinks, and shifts colour with the regime he is in -
 * which is why the dashboard needs no header to say what he is doing.
 */
(function () {
  const GLYPHS = " .`',:;~+*=#%@";
  const HOT_LIMIT = 1400;

  // Eye geometry in field units (the field is normalised by `this.scale`).
  const EYE_X = 0.33;
  const EYE_W = 0.32;
  const EYE_H = 0.125;
  const TILT = 0.22;

  const clamp = (v, lo, hi) => (v < lo ? lo : v > hi ? hi : v);
  const gauss = (x, s) => Math.exp(-(x * x) / (2 * s * s));
  const hash = (n) => {
    const s = Math.sin(n * 127.1) * 43758.5453;
    return s - Math.floor(s);
  };
  const mix = (a, b, k) => Math.round(a + (b - a) * k);

  class EvilFace {
    constructor(canvas) {
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.voice = 0;
      this.speaking = false;
      this.regime = "diffuse";
      this.look = { x: 0, y: 0 };
      this.target = { x: 0, y: 0 };
      this.t = 0;
      this.last = performance.now();
      this.open = 1;
      this.present = true;
      this.blinkAt = 3.5 + Math.random() * 4;
      this.blinkFrom = -10;
      this.resize();
      window.addEventListener("resize", () => this.resize());
      requestAnimationFrame((ts) => this.loop(ts));
    }

    resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      const w = this.canvas.clientWidth || window.innerWidth;
      const h = this.canvas.clientHeight || window.innerHeight;
      this.canvas.width = Math.round(w * dpr);
      this.canvas.height = Math.round(h * dpr);
      this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      this.w = w;
      this.h = h;
      this.cellH = clamp(h / 34, 9, 22);
      this.cellW = this.cellH * 0.55;
      this.cols = Math.ceil(w / this.cellW) + 1;
      this.rows = Math.ceil(h / this.cellH) + 1;
      this.scale = Math.min(w * 0.68, h * 1.28);
      this.cx = w / 2;
      this.cy = h * 0.48;
      this.ctx.font = `${Math.round(this.cellH * 1.05)}px ui-monospace, "SF Mono", Menlo, Consolas, monospace`;
      this.ctx.textBaseline = "top";
    }

    setPointer(nx, ny) {
      this.target.x = clamp(nx, -1, 1);
      this.target.y = clamp(ny, -1, 1);
    }

    setVoice(level) {
      this.voice = clamp(level, 0, 1);
    }

    setSpeaking(on) {
      this.speaking = Boolean(on);
    }

    setRegime(regime) {
      this.regime = String(regime || "diffuse");
    }

    /** Awake or dormant: a sleeping pair of eyes burns low, it does not go out. */
    setPresent(on) {
      this.present = Boolean(on);
    }

    /** The hot colour his eyes burn in for the regime he currently holds. */
    palette() {
      if (this.regime === "convergent") return [255, 176, 128];
      if (this.regime === "structural") return [255, 104, 44];
      return [255, 44, 48];
    }

    /** One eye, as heat (0..1). `s` is -1 for the left socket, 1 for the right. */
    eyeHeat(u, v, s, t) {
      const breathe = 1 + Math.sin(t * 0.9 + s) * 0.02;
      const ex = EYE_X * s + this.look.x * 0.012;
      const ey = this.look.y * 0.012;
      const du = u - ex;
      const dv = (v - ey) / Math.max(0.25, this.open);
      const a = s * TILT;
      const ux = Math.cos(a) * du + Math.sin(a) * dv;
      const uy = -Math.sin(a) * du + Math.cos(a) * dv;

      // Angry almond: tight upper lid slanting down toward the nose, fuller lower lid.
      const w = EYE_W * breathe;
      const up = EYE_H * 0.68 * breathe;
      const down = EYE_H * breathe;
      const hy = uy < 0 ? up : down;
      const k = Math.pow(Math.abs(ux) / w, 2.5) + Math.pow(Math.abs(uy) / hy, 1.6);
      // a thin haze just outside the lid, so the socket has an edge to hold
      if (k >= 1.2) return null;

      const edge = 1 - Math.min(1, k);
      // hollow: the inside of the socket is nearly black, the rim is what burns
      let heat = 0.02 + 0.05 * Math.pow(edge, 0.6);
      heat += 0.62 * gauss(k - 0.93, 0.055);

      // iris: a ring with the slit burning through it
      const ix = ex + this.look.x * 0.032;
      const iy = ey + this.look.y * 0.028;
      const iris = Math.hypot(u - ix, (v - iy) * 1.3);
      const glow = 0.85 + this.voice * 0.55;
      heat += 0.5 * gauss(iris, 0.085) * glow;
      heat += 0.42 * gauss(iris - 0.058, 0.022) * glow;
      const slitW = 0.008 + this.voice * 0.006;
      heat += 1.45 * gauss(u - ix, slitW) * gauss(v - iy, 0.06) * glow;

      // slow pulse so a still face still moves, and grain so it never looks printed
      heat *= 1 + Math.sin(t * 1.4 + s * 2.1) * 0.08;
      heat *= 0.9 + 0.12 * hash(u * 31.7 + v * 17.3 + t * 0.6);
      return clamp(heat * clamp(this.open * 2.4, 0, 1) * (this.present ? 1 : 0.45), 0, 1);
    }

    loop(ts) {
      const dt = Math.min(0.06, (ts - this.last) / 1000 || 0.016);
      this.last = ts;
      this.t += dt;

      this.look.x += (this.target.x - this.look.x) * Math.min(1, dt * 3.4);
      this.look.y += (this.target.y - this.look.y) * Math.min(1, dt * 3.4);

      // a slow blink every few seconds
      if (this.t > this.blinkAt) {
        this.blinkFrom = this.t;
        this.blinkAt = this.t + 4 + Math.random() * 6;
      }
      const bp = (this.t - this.blinkFrom) / 0.28;
      this.open = bp >= 0 && bp <= 1 ? Math.abs(Math.cos(Math.PI * bp)) : 1;

      this.draw();
      requestAnimationFrame((next) => this.loop(next));
    }

    draw() {
      const ctx = this.ctx;
      const t = this.t;
      const S = this.scale;
      ctx.clearRect(0, 0, this.w, this.h);

      const [pr, pg, pb] = this.palette();
      const flare = (0.16 + this.voice * 0.34) * (this.present ? 1 : 0.5);

      // bloom behind the sockets
      for (const s of [-1, 1]) {
        const x = this.cx + EYE_X * s * S + this.look.x * 0.012 * S;
        const y = this.cy + this.look.y * 0.012 * S;
        const bloom = ctx.createRadialGradient(x, y, 0, x, y, S * 0.42);
        bloom.addColorStop(0, `rgba(${pr}, ${pg}, ${pb}, ${(flare * this.open).toFixed(3)})`);
        bloom.addColorStop(0.45, `rgba(${Math.round(pr * 0.5)}, ${Math.round(pg * 0.16)}, ${Math.round(pb * 0.16)}, ${(flare * 0.4 * this.open).toFixed(3)})`);
        bloom.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = bloom;
        ctx.fillRect(x - S * 0.42, y - S * 0.42, S * 0.84, S * 0.84);
      }

      const hot = [];
      for (let ry = 0; ry < this.rows; ry++) {
        let line = "";
        let has = false;
        let rowHeat = 0;
        for (let rx = 0; rx < this.cols; rx++) {
          const x = rx * this.cellW + this.cellW * 0.5;
          const y = ry * this.cellH + this.cellH * 0.5;
          const u = (x - this.cx) / S;
          const v = (y - this.cy) / S;
          let heat = this.eyeHeat(u, v, -1, t);
          const right = this.eyeHeat(u, v, 1, t);
          if (right !== null && (heat === null || right > heat)) heat = right;
          if (heat === null || heat < 0.04) { line += " "; continue; }
          line += GLYPHS[Math.round(heat * (GLYPHS.length - 1))];
          has = true;
          if (heat > rowHeat) rowHeat = heat;
          if (heat > 0.42) hot.push({ rx, ry, heat });
        }
        if (!has) continue;
        const k = Math.pow(rowHeat, 1.5);
        ctx.fillStyle = `rgba(${mix(70, pr, k)}, ${mix(10, pg, k * k)}, ${mix(8, pb, k * k)}, ${(0.18 + rowHeat * 0.82).toFixed(3)})`;
        ctx.fillText(line, 0, ry * this.cellH);
      }

      ctx.save();
      ctx.shadowColor = `rgba(${pr}, ${pg}, ${pb}, 0.9)`;
      ctx.shadowBlur = this.cellH * 0.9;
      for (let i = 0; i < hot.length && i < HOT_LIMIT; i++) {
        const cell = hot[i];
        const k = clamp((cell.heat - 0.42) / 0.58, 0, 1);
        const r = mix(pr, 255, k);
        const g = mix(pg, 236, k * k);
        const b = mix(pb, 214, k * k);
        ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${(0.35 + k * 0.65).toFixed(3)})`;
        ctx.fillText(GLYPHS[Math.round(cell.heat * (GLYPHS.length - 1))],
          cell.rx * this.cellW, cell.ry * this.cellH);
      }
      ctx.restore();
    }
  }

  window.EvilFace = EvilFace;
})();
