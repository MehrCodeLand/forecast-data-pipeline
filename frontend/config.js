// API location. The site is served by nginx, which proxies everything under
// /api to the backend container (see frontend-nginx.conf). So the browser
// only ever talks to THIS origin - no separate API port needs to be open or
// reachable. This is what fixes "the server has data but the website shows
// nothing": the old build pointed the browser at a port it could not reach.
//
// To point at an API elsewhere (e.g. local dev against a running backend),
// set window.API_BASE_URL_OVERRIDE in a script tag before this file.
const API_BASE_URL = (typeof window !== 'undefined' && window.API_BASE_URL_OVERRIDE)
    ? window.API_BASE_URL_OVERRIDE
    : `${window.location.origin}/api`;
