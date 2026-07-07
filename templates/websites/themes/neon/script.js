document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initSmoothScroll();
    initScanIn();
    initYear();
    initContactForm();
});

function initNavigation() {
    const toggle = document.getElementById('mobile-menu');
    const menu = document.getElementById('nav-menu');
    if (!toggle || !menu) return;

    toggle.addEventListener('click', () => menu.classList.toggle('active'));
    menu.querySelectorAll('.nav-link').forEach((link) => {
        link.addEventListener('click', () => menu.classList.remove('active'));
    });
}

function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach((link) => {
        link.addEventListener('click', (event) => {
            const targetId = link.getAttribute('href');
            if (!targetId || targetId === '#') return;
            const target = document.querySelector(targetId);
            if (!target) return;
            event.preventDefault();
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            updateActiveNav(targetId);
        });
    });

    window.addEventListener('scroll', () => {
        const sections = document.querySelectorAll('section[id]');
        const scrollPos = window.scrollY + 120;
        sections.forEach((section) => {
            if (scrollPos >= section.offsetTop && scrollPos < section.offsetTop + section.offsetHeight) {
                updateActiveNav(`#${section.id}`);
            }
        });
    });
}

function updateActiveNav(targetId) {
    document.querySelectorAll('.nav-link').forEach((link) => {
        link.classList.toggle('active', link.getAttribute('href') === targetId);
    });
}

function initScanIn() {
    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                }
            });
        },
        { threshold: 0.12 }
    );

    document.querySelectorAll('.scan-in').forEach((element) => observer.observe(element));
}

function initYear() {
    const year = document.getElementById('current-year');
    if (year) year.textContent = String(new Date().getFullYear());
}

function initContactForm() {
    const form = document.getElementById('contact-form');
    if (!form) return;

    form.addEventListener('submit', (event) => {
        event.preventDefault();
        const data = new FormData(form);
        const name = data.get('name');
        const email = data.get('email');
        const message = data.get('message');
        const ownerEmailEl = document.querySelector('.contact-list a[href^="mailto:"]');
        const ownerEmail = ownerEmailEl ? ownerEmailEl.getAttribute('href')?.replace('mailto:', '') : '';

        if (!ownerEmail) {
            alert('Transmission queued. Please contact the site owner directly.');
            form.reset();
            return;
        }

        const body = encodeURIComponent(`Name: ${name}\nEmail: ${email}\n\nMessage:\n${message}`);
        const subject = encodeURIComponent(`Portfolio contact - from ${name}`);
        window.location.href = `mailto:${ownerEmail}?subject=${subject}&body=${body}`;
        form.reset();
    });
}
