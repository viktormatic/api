/**
 * Zukunvt Landing Page - JavaScript
 * Handles interactivity, animations, and user experience enhancements
 */

(function() {
    'use strict';

    // ==========================================================================
    // DOM Elements
    // ==========================================================================

    const navbar = document.querySelector('.navbar');
    const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    const navLinks = document.querySelector('.nav-links');
    const testimonialCards = document.querySelectorAll('.testimonial-card');
    const testimonialDots = document.querySelectorAll('.testimonial-dots .dot');
    const contactForm = document.getElementById('contactForm');
    const newsletterForms = document.querySelectorAll('.newsletter-form');

    // ==========================================================================
    // Navigation
    // ==========================================================================

    /**
     * Handle navbar scroll effect
     */
    function handleNavbarScroll() {
        if (window.scrollY > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    }

    /**
     * Toggle mobile menu
     */
    function toggleMobileMenu() {
        mobileMenuBtn.classList.toggle('active');
        navLinks.classList.toggle('active');
    }

    /**
     * Close mobile menu when clicking a link
     */
    function closeMobileMenu() {
        mobileMenuBtn.classList.remove('active');
        navLinks.classList.remove('active');
    }

    // Navbar scroll effect
    window.addEventListener('scroll', handleNavbarScroll);
    handleNavbarScroll(); // Initial check

    // Mobile menu toggle
    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener('click', toggleMobileMenu);
    }

    // Close mobile menu on link click
    if (navLinks) {
        navLinks.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', closeMobileMenu);
        });
    }

    // ==========================================================================
    // Smooth Scrolling
    // ==========================================================================

    /**
     * Handle smooth scrolling for anchor links
     */
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href === '#') return;

            e.preventDefault();
            const target = document.querySelector(href);
            if (target) {
                const navHeight = navbar.offsetHeight;
                const targetPosition = target.getBoundingClientRect().top + window.scrollY - navHeight;

                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });

    // ==========================================================================
    // Testimonials Slider
    // ==========================================================================

    let currentTestimonial = 0;
    let testimonialInterval;

    /**
     * Show specific testimonial
     * @param {number} index - Index of testimonial to show
     */
    function showTestimonial(index) {
        // Hide all testimonials
        testimonialCards.forEach(card => {
            card.classList.remove('active');
        });

        // Remove active from all dots
        testimonialDots.forEach(dot => {
            dot.classList.remove('active');
        });

        // Show selected testimonial
        if (testimonialCards[index]) {
            testimonialCards[index].classList.add('active');
        }

        // Activate selected dot
        if (testimonialDots[index]) {
            testimonialDots[index].classList.add('active');
        }

        currentTestimonial = index;
    }

    /**
     * Show next testimonial
     */
    function nextTestimonial() {
        const next = (currentTestimonial + 1) % testimonialCards.length;
        showTestimonial(next);
    }

    /**
     * Start auto-rotation of testimonials
     */
    function startTestimonialAutoplay() {
        testimonialInterval = setInterval(nextTestimonial, 5000);
    }

    /**
     * Stop auto-rotation of testimonials
     */
    function stopTestimonialAutoplay() {
        clearInterval(testimonialInterval);
    }

    // Initialize testimonials
    if (testimonialCards.length > 0 && testimonialDots.length > 0) {
        // Dot click handlers
        testimonialDots.forEach((dot, index) => {
            dot.addEventListener('click', () => {
                stopTestimonialAutoplay();
                showTestimonial(index);
                startTestimonialAutoplay();
            });
        });

        // Start autoplay
        startTestimonialAutoplay();
    }

    // ==========================================================================
    // Form Handling
    // ==========================================================================

    /**
     * Handle contact form submission
     */
    if (contactForm) {
        contactForm.addEventListener('submit', function(e) {
            e.preventDefault();

            // Get form data
            const formData = new FormData(this);
            const data = Object.fromEntries(formData.entries());

            // Simple validation
            if (!data.name || !data.email || !data.subject || !data.message) {
                showNotification('Please fill in all fields', 'error');
                return;
            }

            // Email validation
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(data.email)) {
                showNotification('Please enter a valid email address', 'error');
                return;
            }

            // Simulate form submission
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.textContent = 'Sending...';
            submitBtn.disabled = true;

            // Simulate API call
            setTimeout(() => {
                showNotification('Thank you! Your message has been sent successfully.', 'success');
                this.reset();
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
            }, 1500);
        });
    }

    /**
     * Handle newsletter form submissions
     */
    newsletterForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();

            const emailInput = this.querySelector('input[type="email"]');
            const email = emailInput.value;

            // Email validation
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(email)) {
                showNotification('Please enter a valid email address', 'error');
                return;
            }

            // Simulate subscription
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.textContent = 'Subscribing...';
            submitBtn.disabled = true;

            setTimeout(() => {
                showNotification('Thank you for subscribing to our newsletter!', 'success');
                emailInput.value = '';
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
            }, 1000);
        });
    });

    // ==========================================================================
    // Notifications
    // ==========================================================================

    /**
     * Show notification message
     * @param {string} message - Message to display
     * @param {string} type - Type of notification ('success' or 'error')
     */
    function showNotification(message, type = 'success') {
        // Remove existing notifications
        const existingNotification = document.querySelector('.notification');
        if (existingNotification) {
            existingNotification.remove();
        }

        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <span class="notification-message">${message}</span>
            <button class="notification-close">&times;</button>
        `;

        // Add styles
        notification.style.cssText = `
            position: fixed;
            bottom: 30px;
            right: 30px;
            padding: 16px 24px;
            border-radius: 10px;
            background: ${type === 'success' ? '#10b981' : '#ef4444'};
            color: white;
            font-weight: 500;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
            z-index: 9999;
            display: flex;
            align-items: center;
            gap: 16px;
            animation: slideIn 0.3s ease;
            max-width: 400px;
        `;

        // Add animation keyframes if not already added
        if (!document.getElementById('notification-styles')) {
            const style = document.createElement('style');
            style.id = 'notification-styles';
            style.textContent = `
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes slideOut {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(100%); opacity: 0; }
                }
                .notification-close {
                    background: none;
                    border: none;
                    color: white;
                    font-size: 20px;
                    cursor: pointer;
                    opacity: 0.8;
                    transition: opacity 0.2s;
                }
                .notification-close:hover {
                    opacity: 1;
                }
            `;
            document.head.appendChild(style);
        }

        // Add to DOM
        document.body.appendChild(notification);

        // Close button handler
        notification.querySelector('.notification-close').addEventListener('click', () => {
            removeNotification(notification);
        });

        // Auto-remove after 5 seconds
        setTimeout(() => {
            removeNotification(notification);
        }, 5000);
    }

    /**
     * Remove notification with animation
     * @param {HTMLElement} notification - Notification element to remove
     */
    function removeNotification(notification) {
        if (notification && notification.parentNode) {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {
                notification.remove();
            }, 300);
        }
    }

    // ==========================================================================
    // Scroll Animations
    // ==========================================================================

    /**
     * Animate elements when they enter the viewport
     */
    function initScrollAnimations() {
        const animatedElements = document.querySelectorAll(
            '.service-card, .portfolio-item, .team-member, .about-card, .stat'
        );

        const observerOptions = {
            root: null,
            rootMargin: '0px',
            threshold: 0.1
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);

        animatedElements.forEach(element => {
            element.style.opacity = '0';
            element.style.transform = 'translateY(30px)';
            element.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            observer.observe(element);
        });
    }

    // Initialize scroll animations
    initScrollAnimations();

    // ==========================================================================
    // Active Navigation Highlighting
    // ==========================================================================

    /**
     * Highlight active navigation item based on scroll position
     */
    function highlightActiveNav() {
        const sections = document.querySelectorAll('section[id]');
        const navHeight = navbar.offsetHeight;

        sections.forEach(section => {
            const sectionTop = section.offsetTop - navHeight - 100;
            const sectionHeight = section.offsetHeight;
            const scrollPosition = window.scrollY;

            if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
                const currentId = section.getAttribute('id');

                navLinks.querySelectorAll('a').forEach(link => {
                    link.classList.remove('active');
                    if (link.getAttribute('href') === `#${currentId}`) {
                        link.classList.add('active');
                    }
                });
            }
        });
    }

    window.addEventListener('scroll', highlightActiveNav);
    highlightActiveNav(); // Initial check

    // ==========================================================================
    // Portfolio Hover Effects
    // ==========================================================================

    const portfolioItems = document.querySelectorAll('.portfolio-item');

    portfolioItems.forEach(item => {
        item.addEventListener('mouseenter', function() {
            this.querySelector('.portfolio-overlay').style.opacity = '1';
        });

        item.addEventListener('mouseleave', function() {
            this.querySelector('.portfolio-overlay').style.opacity = '0';
        });
    });

    // ==========================================================================
    // Counter Animation
    // ==========================================================================

    /**
     * Animate number counting
     * @param {HTMLElement} element - Element containing the number
     * @param {number} target - Target number
     * @param {number} duration - Animation duration in ms
     */
    function animateCounter(element, target, duration = 2000) {
        const start = 0;
        const increment = target / (duration / 16);
        let current = start;

        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                element.textContent = target + '+';
                clearInterval(timer);
            } else {
                element.textContent = Math.floor(current) + '+';
            }
        }, 16);
    }

    /**
     * Initialize counter animations when stats are visible
     */
    function initCounters() {
        const statNumbers = document.querySelectorAll('.stat-number');
        let animated = false;

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting && !animated) {
                    animated = true;
                    statNumbers.forEach(stat => {
                        const text = stat.textContent;
                        const number = parseInt(text.replace(/\D/g, ''));
                        if (!isNaN(number)) {
                            animateCounter(stat, number);
                        }
                    });
                    observer.disconnect();
                }
            });
        }, { threshold: 0.5 });

        if (statNumbers.length > 0) {
            observer.observe(statNumbers[0].closest('.about-stats'));
        }
    }

    initCounters();

    // ==========================================================================
    // Utility Functions
    // ==========================================================================

    /**
     * Debounce function to limit function calls
     * @param {Function} func - Function to debounce
     * @param {number} wait - Wait time in ms
     */
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Debounced scroll handler
    const debouncedScrollHandler = debounce(() => {
        handleNavbarScroll();
        highlightActiveNav();
    }, 10);

    window.addEventListener('scroll', debouncedScrollHandler);

    // ==========================================================================
    // Page Load Animation
    // ==========================================================================

    /**
     * Animate page elements on load
     */
    window.addEventListener('load', () => {
        document.body.classList.add('loaded');

        // Animate hero content
        const heroContent = document.querySelector('.hero-content');
        if (heroContent) {
            heroContent.style.opacity = '0';
            heroContent.style.transform = 'translateY(30px)';

            setTimeout(() => {
                heroContent.style.transition = 'opacity 0.8s ease, transform 0.8s ease';
                heroContent.style.opacity = '1';
                heroContent.style.transform = 'translateY(0)';
            }, 100);
        }
    });

    // ==========================================================================
    // Console Message
    // ==========================================================================

    console.log(`
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║   🚀 Welcome to Zukunvt Digital Agency                       ║
    ║                                                              ║
    ║   Shaping Tomorrow's Digital World                           ║
    ║                                                              ║
    ║   Website: www.zukunvt.com                                   ║
    ║   Email: hello@zukunvt.com                                   ║
    ║                                                              ║
    ║   Interested in working with us?                             ║
    ║   We're always looking for talented individuals!             ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    `);

})();
