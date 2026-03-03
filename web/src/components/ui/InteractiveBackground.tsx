import React, { useEffect, useRef } from 'react';

interface InteractiveBackgroundProps {
    className?: string;
}

export default function InteractiveBackground({ className = '' }: InteractiveBackgroundProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        let animationFrameId: number;
        let particles: Particle[] = [];
        let shapeCoordinates: { x: number; y: number; color?: string }[] = [];
        let mouse = { x: -1000, y: -1000, radius: 100 };
        let isVisible = true; // Track tab/page visibility

        // Configuration — scale particles by device capability
        const GAP = 3;
        const isMobile = window.innerWidth < 768;
        const cpuCores = navigator.hardwareConcurrency || 4;
        const MAX_PARTICLES = isMobile ? 600 : cpuCores <= 2 ? 800 : 1200;
        const MOUSE_RADIUS = 120;
        const FRICTION = 0.90;
        const EASE = 0.02;

        // Timing
        let lastStateChange = Date.now();
        let currentState: 'forming' | 'dispersing' = 'forming';
        const HOLD_DURATION = 12000;
        const DISPERSE_DURATION = 8000;

        class Particle {
            x: number;
            y: number;
            vx: number;
            vy: number;
            originX: number;
            originY: number;
            targetX: number;
            targetY: number;
            color: string;
            size: number;

            constructor(x: number, y: number, color: string) {
                this.x = Math.random() * window.innerWidth;
                this.y = Math.random() * window.innerHeight;
                this.originX = Math.random() * window.innerWidth;
                this.originY = Math.random() * window.innerHeight;
                this.targetX = this.originX;
                this.targetY = this.originY;
                this.vx = 0;
                this.vy = 0;
                this.color = color;
                this.size = 1.6;
            }

            draw(context: CanvasRenderingContext2D) {
                context.fillStyle = this.color;
                context.beginPath();
                context.arc(this.x, this.y, this.size, 0, Math.PI * 2);
                context.fill();
            }

            update(width: number, height: number) {
                if (currentState === 'forming' && this.targetX !== -1) {
                    // targetX/Y set during shape assignment
                } else {
                    this.targetX = this.originX;
                    this.targetY = this.originY;

                    this.originX += (Math.random() - 0.5) * 0.5;
                    this.originY += (Math.random() - 0.5) * 0.5;

                    if (this.originX < 0) this.originX = width;
                    if (this.originX > width) this.originX = 0;
                    if (this.originY < 0) this.originY = height;
                    if (this.originY > height) this.originY = 0;
                }

                const dx = this.targetX - this.x;
                const dy = this.targetY - this.y;

                this.vx += dx * EASE;
                this.vy += dy * EASE;

                const dxMouse = mouse.x - this.x;
                const dyMouse = mouse.y - this.y;
                const distMouse = Math.sqrt(dxMouse * dxMouse + dyMouse * dyMouse);

                if (distMouse < MOUSE_RADIUS) {
                    const angle = Math.atan2(dyMouse, dxMouse);
                    const force = (MOUSE_RADIUS - distMouse) / MOUSE_RADIUS;
                    const push = force * 6;

                    this.vx -= Math.cos(angle) * push;
                    this.vy -= Math.sin(angle) * push;
                }

                this.vx *= FRICTION;
                this.vy *= FRICTION;

                this.x += this.vx;
                this.y += this.vy;
            }
        }

        const scanShape = () => {
            const tempCanvas = document.createElement('canvas');
            const tCtx = tempCanvas.getContext('2d');
            if (!tCtx) return;

            tempCanvas.width = canvas.width;
            tempCanvas.height = canvas.height;

            const centerX = canvas.width / 2;
            const centerY = canvas.height / 2;

            const iconSize = 180;
            const iconX = centerX - iconSize / 2;
            const iconY = centerY - 140;

            tCtx.fillStyle = '#6366f1';
            roundRect(tCtx, iconX, iconY, iconSize, iconSize * 0.9, 45, true);

            tCtx.fillStyle = '#ffffff';
            const eyeWidth = 18;
            const eyeHeight = 30;
            const eyeOffset = 50;
            const eyeY = iconY + 70;
            roundRect(tCtx, iconX + eyeOffset, eyeY, eyeWidth, eyeHeight, 8, true);
            roundRect(tCtx, iconX + iconSize - eyeOffset - eyeWidth, eyeY, eyeWidth, eyeHeight, 8, true);

            tCtx.strokeStyle = '#ef4444';
            tCtx.lineWidth = 10;
            tCtx.lineCap = 'round';
            tCtx.beginPath(); tCtx.moveTo(iconX + 15, iconY + 30); tCtx.lineTo(iconX - 15, iconY - 30); tCtx.stroke();
            tCtx.beginPath(); tCtx.moveTo(iconX + iconSize - 15, iconY + 30); tCtx.lineTo(iconX + iconSize + 15, iconY - 30); tCtx.stroke();
            tCtx.fillStyle = '#ef4444';
            tCtx.beginPath(); tCtx.arc(iconX - 15, iconY - 30, 9, 0, Math.PI * 2); tCtx.fill();
            tCtx.beginPath(); tCtx.arc(iconX + iconSize + 15, iconY - 30, 9, 0, Math.PI * 2); tCtx.fill();

            tCtx.fillStyle = '#ffffff';
            tCtx.font = 'bold 90px Inter, sans-serif';
            tCtx.textAlign = 'center';
            tCtx.fillText('PostBot', centerX, iconY + iconSize + 100);

            const imageData = tCtx.getImageData(0, 0, canvas.width, canvas.height);
            const data = imageData.data;

            shapeCoordinates = [];
            for (let y = 0; y < canvas.height; y += GAP) {
                for (let x = 0; x < canvas.width; x += GAP) {
                    const index = (y * canvas.width + x) * 4;
                    if (data[index + 3] > 128) {
                        const r = data[index];
                        const g = data[index + 1];
                        const b = data[index + 2];
                        shapeCoordinates.push({ x, y, color: `rgb(${r},${g},${b})` });
                    }
                }
            }
        };

        const init = () => {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;

            scanShape();

            const particleCount = Math.min(
                Math.max(shapeCoordinates.length, MAX_PARTICLES),
                MAX_PARTICLES
            );

            particles = [];
            for (let i = 0; i < particleCount; i++) {
                const defaultColor = Math.random() > 0.5 ? 'rgba(147, 51, 234, 0.15)' : 'rgba(59, 130, 246, 0.15)';
                particles.push(new Particle(0, 0, defaultColor));
            }
        };

        const updateState = () => {
            const now = Date.now();
            const timeInState = now - lastStateChange;

            if (currentState === 'forming') {
                if (timeInState > HOLD_DURATION) {
                    currentState = 'dispersing';
                    lastStateChange = now;
                    particles.forEach(p => {
                        p.targetX = p.originX;
                        p.targetY = p.originY;
                        p.color = Math.random() > 0.5 ? 'rgba(147, 51, 234, 0.4)' : 'rgba(59, 130, 246, 0.4)';
                    });
                } else {
                    for (let i = 0; i < particles.length; i++) {
                        if (i < shapeCoordinates.length) {
                            particles[i].targetX = shapeCoordinates[i].x;
                            particles[i].targetY = shapeCoordinates[i].y;
                            particles[i].color = shapeCoordinates[i].color!;
                        } else {
                            particles[i].targetX = particles[i].originX;
                            particles[i].targetY = particles[i].originY;
                            particles[i].color = 'rgba(255, 255, 255, 0.05)';
                        }
                    }
                }
            } else if (currentState === 'dispersing') {
                if (timeInState > DISPERSE_DURATION) {
                    currentState = 'forming';
                    lastStateChange = now;
                }
            }
        };

        const animate = () => {
            if (!ctx || !isVisible) {
                // When hidden, keep requesting frames but skip rendering
                animationFrameId = requestAnimationFrame(animate);
                return;
            }

            ctx.clearRect(0, 0, canvas.width, canvas.height);

            updateState();

            const w = canvas.width;
            const h = canvas.height;

            for (let i = 0; i < particles.length; i++) {
                particles[i].update(w, h);
                particles[i].draw(ctx);
            }

            animationFrameId = requestAnimationFrame(animate);
        };

        function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number, fill = false) {
            if (w < 2 * r) r = w / 2;
            if (h < 2 * r) r = h / 2;
            ctx.beginPath();
            ctx.moveTo(x + r, y);
            ctx.arcTo(x + w, y, x + w, y + h, r);
            ctx.arcTo(x + w, y + h, x, y + h, r);
            ctx.arcTo(x, y + h, x, y, r);
            ctx.arcTo(x, y, x + w, y, r);
            ctx.closePath();
            if (fill) ctx.fill();
        }

        // Throttled mouse handler — fire at most every 16ms (~60fps)
        let lastMouseTime = 0;
        const handleMouseMove = (e: MouseEvent) => {
            const now = performance.now();
            if (now - lastMouseTime < 16) return;
            lastMouseTime = now;
            mouse.x = e.clientX;
            mouse.y = e.clientY;
        };

        // Pause rendering when tab is hidden
        const handleVisibilityChange = () => {
            isVisible = !document.hidden;
        };

        // Debounced resize handler
        let resizeTimer: ReturnType<typeof setTimeout>;
        const handleResize = () => {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => init(), 200);
        };

        init();
        animate();

        window.addEventListener('resize', handleResize);
        window.addEventListener('mousemove', handleMouseMove, { passive: true });
        document.addEventListener('visibilitychange', handleVisibilityChange);

        return () => {
            window.removeEventListener('resize', handleResize);
            window.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('visibilitychange', handleVisibilityChange);
            cancelAnimationFrame(animationFrameId);
            clearTimeout(resizeTimer);
        };
    }, []);

    return (
        <canvas
            ref={canvasRef}
            className={`fixed inset-0 pointer-events-none z-0 bg-transparent opacity-[0.055] ${className}`}
            style={{ willChange: 'transform' }}
        />
    );
}
