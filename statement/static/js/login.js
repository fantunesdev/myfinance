import * as services from "./data/services.js";

(async () => {
    if (window.location.pathname == '/login/') {
        let defaults = JSON.parse(sessionStorage.getItem('defaults')),
            version = document.getElementById('version');
        if (!defaults) {
            defaults = await services.getResource('defaults');
        }
        version.innerHTML = defaults.version;
    }
})();