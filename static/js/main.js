// main.js — page behavior for Spendly

document.addEventListener("submit", function (event) {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    if (!form.matches("form[data-confirm]")) return;

    const message = form.dataset.confirm || "Are you sure?";
    if (!window.confirm(message)) {
        event.preventDefault();
    }
});
