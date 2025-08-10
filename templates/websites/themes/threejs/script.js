// Modern Portfolio Theme JavaScript - No 3D Canvas
// Clean implementation focusing on smooth interactions and animations

// Global variables
let isMobile = false;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    detectMobile();
    initNavigation();
    initTypewriter();
    initStarsBackground();
    initSmoothScrolling();
    initScrollAnimations();
    initParallaxEffects();
});

// Detect mobile device
function detectMobile() {
    const mediaQuery = window.matchMedia('(max-width: 768px)');
    isMobile = mediaQuery.matches;

    mediaQuery.addEventListener('change', (event) => {
        isMobile = event.matches;
        // Reinitialize effects on mobile change
        initParallaxEffects();
    });
}

// Navigation functionality
function initNavigation() {
    const navbar = document.querySelector('.navbar');
    const mobileMenu = document.getElementById('mobile-menu');
    const navMenu = document.getElementById('nav-menu');
    let activeSection = '';

    // Scroll effect for navbar
    window.addEventListener('scroll', () => {
        if (window.scrollY > 100) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }

        // Update active section based on scroll position
        updateActiveSection();
    });

    // Mobile menu toggle
    if (mobileMenu && navMenu) {
        mobileMenu.addEventListener('click', function(e) {
            e.stopPropagation();
            mobileMenu.classList.toggle('active');
            navMenu.classList.toggle('active');

            // Trigger staggered animations for mobile menu items
            if (navMenu.classList.contains('active')) {
                const navLinks = navMenu.querySelectorAll('.nav-link');
                navLinks.forEach((link, index) => {
                    link.style.setProperty('--item-index', index);
                });
            }
        });

        // Handle navigation clicks
        const handleNavClick = (e, section) => {
            e.preventDefault();

            // Close mobile menu if open
            if (mobileMenu.classList.contains('active')) {
                mobileMenu.classList.remove('active');
                navMenu.classList.remove('active');
            }

            // Update active section
            updateActiveLink(section);

            // Smooth scroll to section
            const targetElement = document.getElementById(section);
            if (targetElement) {
                const offsetTop = targetElement.offsetTop - 80; // Account for fixed navbar
                window.scrollTo({
                    top: offsetTop,
                    behavior: 'smooth'
                });
            }
        };

        // Add click handlers to all nav links
        const navLinks = document.querySelectorAll('.nav-link');

        navLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                const section = this.getAttribute('data-section');
                if (section) {
                    handleNavClick(e, section);
                } else { // for anchor links like #about
                    const href = this.getAttribute('href');
                    if (href && href.startsWith('#')) {
                        const sectionId = href.substring(1);
                        const targetElement = document.getElementById(sectionId);
                        if (targetElement) {
                            handleNavClick(e, sectionId);
                        }
                    }
                }
            });
        });

        // Close mobile menu when clicking outside
        document.addEventListener('click', function(e) {
            if (!navMenu.contains(e.target) && !mobileMenu.contains(e.target)) {
                if (navMenu.classList.contains('active')) {
                    mobileMenu.classList.remove('active');
                    navMenu.classList.remove('active');
                }
            }
        });
    }

    // Initialize staggered animations for desktop nav items
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach((link, index) => {
        link.style.setProperty('--item-index', index);
    });

    // Update active section based on scroll position
    function updateActiveSection() {
        const sections = document.querySelectorAll('.section, .hero');
        const scrollPos = window.scrollY + 100;

        sections.forEach(section => {
            const top = section.offsetTop;
            const bottom = top + section.offsetHeight;

            if (scrollPos >= top && scrollPos <= bottom) {
                const sectionId = section.id;
                if (sectionId && sectionId !== activeSection) {
                    activeSection = sectionId;
                    updateActiveLink(sectionId);
                }
            }
        });
    }

    // Update active link styling
    function updateActiveLink(section) {
        const allLinks = document.querySelectorAll('.nav-link');
        allLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('data-section') === section) {
                link.classList.add('active');
            }
        });
    }
}

// Typewriter effect
function initTypewriter() {
    const typewriterElement = document.querySelector('.typewriter-text');
    if (!typewriterElement) return;

    // Get job titles from data attribute or use defaults
    const dataJobTitles = typewriterElement?.dataset.jobTitles;

    let texts;
    if (dataJobTitles) {
        try {
            texts = JSON.parse(dataJobTitles);
        } catch (e) {
            texts = [];
        }
    }

    // Fallback to default job titles if no data available or parsing failed
    if (!texts || texts.length === 0) {
        texts = [
            "Software Engineer"
        ];
    }

    let currentIndex = 0;
    let displayText = '';
    let isTyping = true;
    let isDeleting = false;

    function typeText() {
        const currentText = texts[currentIndex];

        if (isTyping && !isDeleting) {
            if (displayText.length < currentText.length) {
                displayText = currentText.slice(0, displayText.length + 1);
                typewriterElement.innerHTML = displayText + '<span class="typewriter-cursor">|</span>';
                setTimeout(typeText, 100); // Typing speed
            } else {
                isTyping = false;
                setTimeout(() => {
                    isDeleting = true;
                    typeText();
                }, 2000); // Pause before deleting
            }
        } else if (isDeleting) {
            if (displayText.length > 0) {
                displayText = displayText.slice(0, -1);
                typewriterElement.innerHTML = displayText + '<span class="typewriter-cursor">|</span>';
                setTimeout(typeText, 50); // Deleting speed
            } else {
                isDeleting = false;
                isTyping = true;
                currentIndex = (currentIndex + 1) % texts.length;
                setTimeout(typeText, 500); // Pause before next text
            }
        }
    }

    typeText();
}

// Animated stars background (CSS-based, no 3D)
function initStarsBackground() {
    const starsContainer = document.getElementById('stars-background');
    if (!starsContainer) return;

    // Create additional floating elements for visual interest
    for (let i = 0; i < 50; i++) {
        const star = document.createElement('div');
        star.className = 'floating-star';
        star.style.cssText = `
            position: absolute;
            width: ${Math.random() * 3 + 1}px;
            height: ${Math.random() * 3 + 1}px;
            background: rgba(255, 255, 255, ${Math.random() * 0.8 + 0.2});
            border-radius: 50%;
            left: ${Math.random() * 100}%;
            top: ${Math.random() * 100}%;
            animation: floatStars ${Math.random() * 10 + 5}s ease-in-out infinite;
            animation-delay: ${Math.random() * 5}s;
        `;
        starsContainer.appendChild(star);
    }

    // Add floating animation CSS
    const style = document.createElement('style');
    style.textContent = `
        @keyframes floatStars {
            0%, 100% { transform: translateY(0px) translateX(0px); opacity: 0.5; }
            25% { transform: translateY(-10px) translateX(5px); opacity: 1; }
            50% { transform: translateY(-5px) translateX(-5px); opacity: 0.7; }
            75% { transform: translateY(-15px) translateX(3px); opacity: 0.9; }
        }
    `;
    document.head.appendChild(style);
}

// Smooth scrolling for anchor links
function initSmoothScrolling() {
    const links = document.querySelectorAll('a[href^="#"]');

    links.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();

            const targetId = this.getAttribute('href');
            const targetSection = document.querySelector(targetId);

            if (targetSection) {
                const offsetTop = targetSection.offsetTop - 70; // Account for fixed navbar

                window.scrollTo({
                    top: offsetTop,
                    behavior: 'smooth'
                });

                // Update active nav link
                updateActiveNavLink(targetId);
            }
        });
    });
}

// Update active navigation link
function updateActiveNavLink(targetId) {
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === targetId) {
            link.classList.add('active');
        }
    });
}

// Scroll animations for elements
function initScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');

                // Add staggered animation for child elements
                const childElements = entry.target.querySelectorAll('.experience-card, .education-card, .project-card, .award-card, .skill-tag');
                childElements.forEach((child, index) => {
                    setTimeout(() => {
                        child.classList.add('visible');
                    }, index * 100); // Stagger by 100ms
                });
            }
        });
    }, observerOptions);

    // Observe all sections and cards
    const elementsToAnimate = document.querySelectorAll(
        '.section, .experience-card, .education-card, .project-card, .award-card, .publication-card'
    );

    elementsToAnimate.forEach(element => {
        element.classList.add('fade-in');
        observer.observe(element);
    });

    // Special animation for skills
    const skillTags = document.querySelectorAll('.skill-tag');
    skillTags.forEach((tag, index) => {
        tag.classList.add('slide-up');
        tag.style.animationDelay = `${index * 50}ms`;
    });

    // Observe skill categories
    const skillCategories = document.querySelectorAll('.skill-category');
    skillCategories.forEach(category => {
        observer.observe(category);
    });
}

// Parallax effects for enhanced visual appeal
function initParallaxEffects() {
    if (isMobile) return; // Skip parallax on mobile for performance

    window.addEventListener('scroll', () => {
        const scrollTop = window.pageYOffset;

        // Parallax for hero section
        const heroSection = document.querySelector('.hero');
        if (heroSection) {
            const parallaxSpeed = 0.5;
            heroSection.style.transform = `translateY(${scrollTop * parallaxSpeed}px)`;
        }

        // Parallax for section backgrounds
        const sections = document.querySelectorAll('.section-alt');
        sections.forEach((section, index) => {
            const rect = section.getBoundingClientRect();
            const speed = 0.2 + (index * 0.1);

            if (rect.top < window.innerHeight && rect.bottom > 0) {
                const yPos = -(rect.top * speed);
                section.style.backgroundPosition = `center ${yPos}px`;
            }
        });
    });
}

// Add interactive hover effects for cards
document.addEventListener('DOMContentLoaded', function() {
    const cards = document.querySelectorAll('.experience-card, .education-card, .project-card, .award-card');

    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-10px) scale(1.02)';
        });

        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });
});

// Scroll progress indicator
function initScrollProgress() {
    const progressBar = document.createElement('div');
    progressBar.className = 'scroll-progress';
    progressBar.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 0%;
        height: 3px;
        background: linear-gradient(90deg, var(--primary-color), var(--accent-color));
        z-index: 1001;
        transition: width 0.1s ease;
    `;
    document.body.appendChild(progressBar);

    window.addEventListener('scroll', () => {
        const scrollTop = window.pageYOffset;
        const docHeight = document.documentElement.scrollHeight - window.innerHeight;
        const scrollPercent = (scrollTop / docHeight) * 100;
        progressBar.style.width = scrollPercent + '%';
    });
}

// Initialize scroll progress
initScrollProgress();

// Add smooth reveal animation for text elements
function initTextAnimations() {
    const textElements = document.querySelectorAll('.section-title, .section-subtitle, .hero-title, .hero-subtitle');

    const textObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.animation = 'fadeInUp 0.8s ease forwards';
            }
        });
    }, { threshold: 0.3 });

    textElements.forEach(element => {
        element.style.opacity = '0';
        element.style.transform = 'translateY(30px)';
        textObserver.observe(element);
    });

    // Add CSS animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fadeInUp {
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
    `;
    document.head.appendChild(style);
}

// Initialize text animations
initTextAnimations();

// Add dynamic theme color updates
function initDynamicColors() {
    const sections = document.querySelectorAll('.section');
    const colors = [
        '#915EFF', '#00BFA6', '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57', '#FF9FF3'
    ];

    sections.forEach((section, index) => {
        const color = colors[index % colors.length];
        section.style.setProperty('--section-accent', color);
    });
}

// Initialize dynamic colors
initDynamicColors();

// Performance optimization: Throttle scroll events
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Apply throttling to scroll events
const throttledScrollHandler = throttle(() => {
    // Consolidated scroll handler for performance
    const scrollTop = window.pageYOffset;

    // Update navbar
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        navbar.classList.toggle('scrolled', scrollTop > 100);
    }

    // Update scroll progress
    const progressBar = document.querySelector('.scroll-progress');
    if (progressBar) {
        const docHeight = document.documentElement.scrollHeight - window.innerHeight;
        const scrollPercent = (scrollTop / docHeight) * 100;
        progressBar.style.width = scrollPercent + '%';
    }
}, 16); // ~60fps

window.addEventListener('scroll', throttledScrollHandler);
