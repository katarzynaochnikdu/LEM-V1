window.LEMShared = (function () {
    function escHtml(text) {
        if (text == null) return "";
        const d = document.createElement("div");
        d.textContent = String(text);
        return d.innerHTML;
    }

    async function getCurrentUser() {
        const resp = await fetch("/api/auth/me");
        if (!resp.ok) {
            throw new Error("UNAUTHORIZED");
        }
        return resp.json();
    }

    async function ensureAuth(onUser) {
        try {
            const user = await getCurrentUser();
            if (typeof onUser === "function") onUser(user);
            return user;
        } catch (_) {
            window.location.href = "/login";
            return null;
        }
    }

    async function doLogout() {
        await fetch("/api/auth/logout", { method: "POST" });
        window.location.href = "/login";
    }

    function setActiveNav(pathname) {
        const links = document.querySelectorAll(".nav-tabs a");
        links.forEach((a) => {
            if (a.getAttribute("href") === pathname) a.classList.add("active");
            else a.classList.remove("active");
        });
    }

    function showToast(message, isError) {
        let toast = document.getElementById("toast");
        if (!toast) {
            toast = document.createElement("div");
            toast.id = "toast";
            toast.className = "toast";
            document.body.appendChild(toast);
        }
        toast.textContent = message;
        toast.className = "toast visible " + (isError ? "err" : "ok");
        setTimeout(() => {
            toast.className = "toast";
        }, 2800);
    }

    return {
        escHtml,
        ensureAuth,
        doLogout,
        setActiveNav,
        showToast,
    };
})();
