// API location. Auto-detects the host so the same build works on localhost
// and on a deployed server: the frontend is served on port 8038 and the API
// is published on port 8342 of the SAME machine, so we reuse the hostname
// the visitor used to reach the site. (The old hardcoded
// 'http://localhost:8342' pointed at the visitor's own computer, which is
// why data did not load for anyone browsing from another device.)
//
// To force a different API location (e.g. behind a reverse proxy), define
// window.API_BASE_URL_OVERRIDE in a script tag before this file.
const API_BASE_URL = (typeof window !== 'undefined' && window.API_BASE_URL_OVERRIDE)
    ? window.API_BASE_URL_OVERRIDE
    : `${window.location.protocol}//${window.location.hostname}:8342`;
