#!/bin/sh
# Prepares /data before Node-RED starts:
#   1. installs the pinned extra nodes (needs access to the npm registry);
#   2. copies the declarative flows of the chart (replacing editor changes);
#   3. writes flows_cred.json with the MQTT credentials from the Secret;
#   4. writes the bcrypt hash of the editor password.
set -eu
cd /data
if [ ! -f package.json ]; then
  echo '{"name":"node-red-project","private":true,"dependencies":{}}' > package.json
fi
for m in ${EXTRA_NODES}; do
  if [ ! -d "node_modules/${m%@*}" ]; then
    npm install --no-audit --no-fund --omit=dev "${m}"
  fi
done
cp /chart/flows.json /data/flows.json
umask 077
node -e 'console.log(JSON.stringify({broker: {user: process.env.MQTT_USERNAME, password: process.env.MQTT_PASSWORD}}))' > /data/flows_cred.json
if [ -n "${NODE_RED_ADMIN_PASSWORD:-}" ]; then
  node -e 'console.log(require("/usr/src/node-red/node_modules/bcryptjs").hashSync(process.env.NODE_RED_ADMIN_PASSWORD, 10))' > /data/.admin_hash
fi
echo "node-red data prepared; extra nodes: ${EXTRA_NODES}"
