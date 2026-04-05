document.addEventListener("DOMContentLoaded", function () {
    const menuToggle = document.getElementById("menuToggle");
    const navLinks = document.getElementById("navLinks");

    if (menuToggle && navLinks) {
        menuToggle.addEventListener("click", function () {
            navLinks.classList.toggle("show");
        });
    }

    const qtyMinus = document.getElementById("qtyMinus");
    const qtyPlus = document.getElementById("qtyPlus");
    const quantityInput = document.getElementById("quantityInput");

    if (qtyMinus && qtyPlus && quantityInput) {
        qtyMinus.addEventListener("click", function () {
            let value = parseInt(quantityInput.value || "1");

            if (value > 1) {
                quantityInput.value = value - 1;
            }
        });

        qtyPlus.addEventListener("click", function () {
            let value = parseInt(quantityInput.value || "1");
            quantityInput.value = value + 1;
        });
    }

    const productCards = document.querySelectorAll(".product-card");

    productCards.forEach(function (card, index) {
        card.style.opacity = "0";
        card.style.transform = "translateY(20px)";

        setTimeout(function () {
            card.style.transition = "0.5s ease";
            card.style.opacity = "1";
            card.style.transform = "translateY(0)";
        }, index * 80);
    });
});