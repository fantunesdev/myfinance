import { setupPhotoReordering } from './dream-photo-order.js';

const dialog = document.querySelector('.dream-photo-dialog');
let links = [...document.querySelectorAll('.dream-photo-open')];
const grid = document.querySelector('.dream-photo-grid');
setupPhotoReordering(grid);
const addPhotos = document.querySelector('[data-photo-add]');
const uploadForm = document.querySelector('#dream-photo-upload');

if (addPhotos && uploadForm) {
    const fileInput = uploadForm.querySelector('input[type="file"]');
    const selection = uploadForm.querySelector('[data-photo-selection]');
    fileInput.addEventListener('change', () => {
        const count = fileInput.files.length;
        selection.hidden = count === 0;
        selection.textContent = count === 1 ? '1 foto selecionada' : `${count} fotos selecionadas`;
    });
    addPhotos.addEventListener('click', () => {
        uploadForm.hidden = !uploadForm.hidden;
        addPhotos.setAttribute('aria-expanded', String(!uploadForm.hidden));
    });
}

if (dialog && links.length) {
    const track = dialog.querySelector('.dream-photo-track');
    const stage = dialog.querySelector('.dream-photo-stage');
    const previous = dialog.querySelector('[data-photo-prev]');
    const next = dialog.querySelector('[data-photo-next]');
    const play = dialog.querySelector('[data-photo-play]');
    const counter = dialog.querySelector('[data-photo-counter]');
    const fullscreen = dialog.querySelector('[data-photo-fullscreen]');
    const viewer = dialog.querySelector('.dream-photo-viewer');
    const slides = new Map();
    let index = 0;
    let opener;
    let touchStart;
    let timer;
    let playing = false;
    play.hidden = links.length < 2;

    function setFullscreen(enabled) {
        dialog.classList.toggle('is-fullscreen', enabled);
        fullscreen.setAttribute('aria-label', enabled ? 'Sair da tela inteira' : 'Tela inteira');
        fullscreen.querySelector('i').className = enabled ? 'fa-solid fa-compress' : 'fa-solid fa-expand';
    }

    function exitFullscreen() {
        setFullscreen(false);
        if (document.fullscreenElement === viewer) {
            document.exitFullscreen().catch(() => {});
        }
    }

    async function toggleFullscreen() {
        pause();
        if (dialog.classList.contains('is-fullscreen')) {
            exitFullscreen();
            return;
        }
        setFullscreen(true);
        try {
            await viewer.requestFullscreen?.();
        } catch {
            // Keep the viewport-sized layout when native fullscreen is unavailable.
        }
    }

    fullscreen.addEventListener('click', toggleFullscreen);
    document.addEventListener('fullscreenchange', () => {
        if (document.fullscreenElement !== viewer) setFullscreen(false);
    });
    dialog.addEventListener('cancel', (event) => {
        if (dialog.classList.contains('is-fullscreen')) {
            event.preventDefault();
            exitFullscreen();
        }
    });

    function pause() {
        clearTimeout(timer);
        playing = false;
        play.textContent = 'Reproduzir';
        play.setAttribute('aria-label', 'Reproduzir apresentação');
    }

    function scheduleNext() {
        clearTimeout(timer);
        timer = setTimeout(() => {
            showPhoto(index + 1);
            if (index === links.length - 1) pause();
            else scheduleNext();
        }, 5000);
    }

    function start() {
        if (index === links.length - 1) showPhoto(0);
        playing = true;
        play.textContent = 'Pausar';
        play.setAttribute('aria-label', 'Pausar apresentação');
        scheduleNext();
    }

    function navigate(position) {
        pause();
        showPhoto(position);
    }

    // Load full images only as the visitor explores the carousel.
    links.forEach((link) => {
        const slide = document.createElement('div');
        slide.className = 'dream-photo-slide';
        const img = document.createElement('img');
        img.alt = link.querySelector('img').alt;
        img.dataset.src = link.href;
        const expand = document.createElement('a');
        expand.className = 'dream-photo-expand';
        expand.href = link.href;
        expand.setAttribute('aria-label', 'Alternar tela inteira');
        expand.addEventListener('click', (event) => {
            event.preventDefault();
            toggleFullscreen();
        });
        expand.append(img);
        slide.append(expand);
        track.append(slide);
        slides.set(link, slide);
    });

    grid.addEventListener('dream-photos-reordered', () => {
        links = [...grid.querySelectorAll('.dream-photo-open')];
        links.forEach((link) => {
            const slide = slides.get(link);
            slide.querySelector('img').alt = link.querySelector('img').alt;
            track.append(slide);
        });
    });

    function showPhoto(position) {
        index = Math.max(0, Math.min(position, links.length - 1));
        [...track.children].forEach((slide, slideIndex) => {
            slide.setAttribute('aria-hidden', String(slideIndex !== index));
            slide.querySelector('a').tabIndex = slideIndex === index ? 0 : -1;
            const img = slide.querySelector('img');
            if (Math.abs(slideIndex - index) <= 1 && !img.getAttribute('src')) {
                img.src = img.dataset.src;
            }
        });
        track.style.transform = `translateX(-${index * 100}%)`;
        counter.textContent = `${index + 1} de ${links.length}`;
        previous.disabled = index === 0;
        next.disabled = index === links.length - 1;
    }

    links.forEach((link) => {
        link.addEventListener('click', (event) => {
            if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
            event.preventDefault();
            opener = link;
            const position = links.indexOf(link);
            track.style.transition = 'none';
            showPhoto(position);
            dialog.showModal();
            document.body.classList.add('dream-photo-viewing');
            // Position the chosen photo before enabling slide transitions.
            track.getBoundingClientRect();
            track.style.transition = '';
            if (position < links.length - 1 && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
                start();
            }
        });
    });

    previous.addEventListener('click', () => navigate(index - 1));
    next.addEventListener('click', () => navigate(index + 1));
    play.addEventListener('click', () => { if (playing) pause(); else start(); });
    dialog.querySelector('[data-photo-close]').addEventListener('click', () => dialog.close());
    dialog.addEventListener('close', () => {
        pause();
        exitFullscreen();
        document.body.classList.remove('dream-photo-viewing');
        opener?.focus();
    });
    document.addEventListener('keydown', (event) => {
        if (!dialog.open) return;
        if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
            event.preventDefault();
            navigate(index + (event.key === 'ArrowLeft' ? -1 : 1));
        }
    });
    dialog.addEventListener('click', (event) => {
        const bounds = dialog.getBoundingClientRect();
        if (event.target === dialog && (event.clientX < bounds.left || event.clientX > bounds.right ||
            event.clientY < bounds.top || event.clientY > bounds.bottom)) dialog.close();
    });
    stage.addEventListener('touchstart', (event) => {
        const touch = event.touches.length === 1 ? event.touches[0] : null;
        touchStart = touch ? { x: touch.clientX, y: touch.clientY } : null;
    }, { passive: true });
    stage.addEventListener('touchend', (event) => {
        if (!touchStart) return;
        const dx = event.changedTouches[0].clientX - touchStart.x;
        const dy = event.changedTouches[0].clientY - touchStart.y;
        if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)) {
            navigate(index + (dx < 0 ? 1 : -1));
        }
        touchStart = null;
    }, { passive: true });
    stage.addEventListener('touchcancel', () => { touchStart = null; });
    document.addEventListener('visibilitychange', () => { if (document.hidden) pause(); });
}
