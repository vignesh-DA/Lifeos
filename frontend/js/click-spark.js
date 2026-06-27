class ClickSpark extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  connectedCallback() {
    this.sparkColor = this.getAttribute('spark-color') || '#7C5CFF';
    this.sparkSize = parseFloat(this.getAttribute('spark-size')) || 10;
    this.sparkRadius = parseFloat(this.getAttribute('spark-radius')) || 15;
    this.sparkCount = parseInt(this.getAttribute('spark-count')) || 8;
    this.duration = parseInt(this.getAttribute('duration')) || 400;
    this.easing = this.getAttribute('easing') || 'ease-out';
    this.extraScale = parseFloat(this.getAttribute('extra-scale')) || 1.0;

    this.sparks = [];
    this.startTime = null;
    this.animationId = null;

    this.render();
    this.canvas = this.shadowRoot.querySelector('canvas');
    this.ctx = this.canvas.getContext('2d');
    
    this.resizeCanvas = this.resizeCanvas.bind(this);
    this.handleClick = this.handleClick.bind(this);
    this.draw = this.draw.bind(this);
    
    window.addEventListener('resize', this.resizeCanvas);
    this.resizeCanvas();
    
    document.addEventListener('click', this.handleClick);
    this.animationId = requestAnimationFrame(this.draw);
  }

  disconnectedCallback() {
    window.removeEventListener('resize', this.resizeCanvas);
    cancelAnimationFrame(this.animationId);
    document.removeEventListener('click', this.handleClick);
  }

  render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          position: fixed;
          top: 0;
          left: 0;
          width: 100vw;
          height: 100vh;
          pointer-events: none;
          z-index: 99999;
        }
        canvas {
          width: 100%;
          height: 100%;
          display: block;
        }
      </style>
      <canvas></canvas>
    `;
  }

  resizeCanvas() {
    if (this.canvas.width !== window.innerWidth || this.canvas.height !== window.innerHeight) {
      this.canvas.width = window.innerWidth;
      this.canvas.height = window.innerHeight;
    }
  }

  easeFunc(t) {
    switch (this.easing) {
      case 'linear':
        return t;
      case 'ease-in':
        return t * t;
      case 'ease-in-out':
        return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
      default:
        return t * (2 - t);
    }
  }

  draw(timestamp) {
    if (!this.startTime) {
      this.startTime = timestamp;
    }
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    this.sparks = this.sparks.filter(spark => {
      const elapsed = timestamp - spark.startTime;
      if (elapsed >= this.duration) {
        return false;
      }

      const progress = elapsed / this.duration;
      const eased = this.easeFunc(progress);

      const distance = eased * this.sparkRadius * this.extraScale;
      const lineLength = this.sparkSize * (1 - eased);

      const x1 = spark.x + distance * Math.cos(spark.angle);
      const y1 = spark.y + distance * Math.sin(spark.angle);
      const x2 = spark.x + (distance + lineLength) * Math.cos(spark.angle);
      const y2 = spark.y + (distance + lineLength) * Math.sin(spark.angle);

      this.ctx.strokeStyle = this.sparkColor;
      this.ctx.lineWidth = 2;
      this.ctx.lineCap = 'round';
      this.ctx.beginPath();
      this.ctx.moveTo(x1, y1);
      this.ctx.lineTo(x2, y2);
      this.ctx.stroke();

      return true;
    });

    this.animationId = requestAnimationFrame(this.draw);
  }

  handleClick(e) {
    const x = e.clientX;
    const y = e.clientY;

    const now = performance.now();
    const newSparks = Array.from({ length: this.sparkCount }, (_, i) => ({
      x,
      y,
      angle: (2 * Math.PI * i) / this.sparkCount,
      startTime: now
    }));

    this.sparks.push(...newSparks);
  }
}

customElements.define('click-spark', ClickSpark);
