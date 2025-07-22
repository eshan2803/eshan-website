document.addEventListener('DOMContentLoaded', () => {
    // Select the header-wrapper if it exists, otherwise select the header
    const stickyElement = document.querySelector('#header-wrapper') || document.querySelector('header');

    if (stickyElement) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 0) {
                stickyElement.classList.add('scrolled');
            } else {
                stickyElement.classList.remove('scrolled');
            }
        });
    }
});
