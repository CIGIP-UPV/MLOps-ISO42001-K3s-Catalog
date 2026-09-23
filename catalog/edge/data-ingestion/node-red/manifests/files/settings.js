// Node-RED settings for the edge-node-red chart.
// Flows are declared in files/flows.json and copied to /data at start-up;
// credentials and the editor password hash are written by the init
// container from Kubernetes Secrets.
const fs = require('fs');
const hashFile = '/data/.admin_hash';
const adminHash = fs.existsSync(hashFile) ? fs.readFileSync(hashFile, 'utf8').trim() : '';

module.exports = {
    uiPort: process.env.PORT || 1880,
    flowFile: 'flows.json',
    // flows_cred.json is generated at start-up from Secrets and never stored
    // in git, so it does not need a second layer of encryption.
    credentialSecret: false,
    httpNodeRoot: '/',
    httpAdminRoot: '/admin',
    // Editor authentication (B.6.1.3.1).
    adminAuth: adminHash ? {
        type: 'credentials',
        users: [{ username: process.env.NODE_RED_ADMIN_USER || 'admin', password: adminHash, permissions: '*' }]
    } : undefined,
    functionExternalModules: false,
    logging: { console: { level: 'info', metrics: false, audit: true } },
    editorTheme: { projects: { enabled: false } }
};
