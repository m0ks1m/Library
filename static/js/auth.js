document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("loginForm");
    const errorMessage = document.getElementById("errorMessage");

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const login = form.username.value.trim();
        const password = form.password.value;

        try {
            const response = await fetch("/api/login", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ login, password })
            });

            const result = await response.json();

            if (response.ok) {
                // Успешный вход — перенаправление на защищенную страницу
                window.location.href = "/";
            } else {
                // Показать сообщение об ошибке
                errorMessage.style.display = "block";
                errorMessage.textContent = result.message || "Ошибка входа";
            }

        } catch (error) {
            console.error("Ошибка при входе:", error);
            errorMessage.style.display = "block";
            errorMessage.textContent = "Ошибка сервера. Попробуйте позже.";
        }
    });
});
