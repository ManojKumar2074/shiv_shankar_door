// ============================================================
// SHIV SHANKAR DOOR — Main JavaScript
// ============================================================

document.addEventListener('DOMContentLoaded', () => {

    // --- Navigation Scroll Effect ---
    const nav = document.getElementById('mainNav');
    if (nav) {
        const onScroll = () => {
            nav.classList.toggle('scrolled', window.scrollY > 30);
        };
        window.addEventListener('scroll', onScroll, { passive: true });
        onScroll();
    }

    // --- Mobile Menu Toggle ---
    const hamburger = document.getElementById('navToggle');
    const mobileMenu = document.getElementById('mobileMenu');
    if (hamburger && mobileMenu) {
        hamburger.addEventListener('click', () => {
            mobileMenu.classList.toggle('open');
            hamburger.classList.toggle('open');
        });
    }

    // --- Intersection Observer (Reveal animations) ---
    const reveals = document.querySelectorAll('.door-card, .category-card, .section__header, .philosophy-card, .material-card, .ai-how-card, .contact-detail');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry, i) => {
            if (entry.isIntersecting) {
                entry.target.classList.add('reveal');
                setTimeout(() => {
                    entry.target.classList.add('revealed');
                }, i * 60);
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });
    reveals.forEach(el => observer.observe(el));

    // --- Auto-dismiss messages ---
    const messages = document.querySelectorAll('.message');
    messages.forEach(msg => {
        setTimeout(() => {
            msg.style.opacity = '0';
            msg.style.transform = 'translateX(20px)';
            setTimeout(() => msg.remove(), 400);
        }, 5000);
    });

    // --- Price slider live update (gallery) ---
    const slider = document.getElementById('priceSlider');
    const display = document.getElementById('priceDisplay');
    if (slider && display) {
        slider.addEventListener('input', () => {
            const val = parseInt(slider.value);
            display.textContent = '₹' + val.toLocaleString('en-IN');
        });
    }

    // --- Smooth hover for door images ---
    document.querySelectorAll('.door-card__image-wrap').forEach(wrap => {
        wrap.addEventListener('mouseenter', function() {
            this.querySelector('.door-card__image').style.transform = 'scale(1.05)';
        });
        wrap.addEventListener('mouseleave', function() {
            this.querySelector('.door-card__image').style.transform = 'scale(1)';
        });
    });

    // --- File upload drag over ---
    const fileUpload = document.getElementById('fileUpload');
    if (fileUpload) {
        fileUpload.addEventListener('dragover', (e) => {
            e.preventDefault();
            fileUpload.style.borderColor = 'var(--gold)';
        });
        fileUpload.addEventListener('dragleave', () => {
            fileUpload.style.borderColor = '';
        });
        fileUpload.addEventListener('drop', (e) => {
            e.preventDefault();
            fileUpload.style.borderColor = '';
        });
    }

});
