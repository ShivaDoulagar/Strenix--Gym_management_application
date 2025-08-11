document.addEventListener("DOMContentLoaded", function() {
    
    // Stagger animation for elements
    // Add the class "stagger-in" to any container
    // and its direct children will fade in one by one.
    const staggeredContainers = document.querySelectorAll('.stagger-in');
    staggeredContainers.forEach(container => {
        const elements = container.children;
        for (let i = 0; i < elements.length; i++) {
            elements[i].style.setProperty('--stagger-delay', (i * 100) + 'ms');
        }
    });

    // Add a class to the navbar when scrolling
    const navbar = document.querySelector('.navbar');
    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    });
});