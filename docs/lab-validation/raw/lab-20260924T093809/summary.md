# Laboratory validation run: summary

| Phase | PASS | FAIL | SKIP |
|---|---|---|---|
| netpol | 10 | 3 | 1 |

| ID | Result | Name | Seconds | Evidence | Detail |
|---|---|---|---|---|---|
| N-CANARY | FAIL | NetworkPolicies are enforced on every node (pod behind a deny-all policy) | 34 | netpol/N-CANARY.txt | edgenode01: client in lab-np-outside -> pod 10.42.2.95:8080 behind a deny-all ingress policy: CONNECTED kb2: client in lab-np-outside -> pod |
| N00 | PASS | namespace outside the catalog -> Internet (control, no policy) (expected: allow) | 0 | netpol/N00.txt | CONNECTED |
| N01 | PASS | edge -> platform TimescaleDB (consolidation conduit) (expected: allow) | 0 | netpol/N01.txt | CONNECTED |
| N02 | PASS | edge -> MLflow (version sync conduit) (expected: allow) | 0 | netpol/N02.txt | CONNECTED |
| N03 | PASS | edge -> edge PostgreSQL (same namespace) (expected: allow) | 0 | netpol/N03.txt | destination on edgenode01, which does not enforce NetworkPolicies (N-CANARY); CONNECTED |
| N04 | PASS | edge -> MinIO (no conduit) (expected: deny) | 0 | netpol/N04.txt | BLOCKED |
| N05 | PASS | edge -> Zammad (no conduit) (expected: deny) | 0 | netpol/N05.txt | BLOCKED |
| N06 | FAIL | namespace outside the catalog -> edge PostgreSQL (default deny ingress) (expected: deny) | 0 | netpol/N06.txt | destination on edgenode01, which does not enforce NetworkPolicies (N-CANARY); CONNECTED |
| N07 | PASS | mlops -> MinIO (artefact conduit) (expected: allow) | 0 | netpol/N07.txt | CONNECTED |
| N08 | FAIL | mlops -> Internet (default deny egress) (expected: deny) | 0 | netpol/N08.txt | CONNECTED |
| N09 | PASS | security -> platform PostgreSQL (Keycloak database) (expected: allow) | 0 | netpol/N09.txt | CONNECTED |
| N10 | PASS | helpdesk -> MLflow (no conduit) (expected: deny) | 0 | netpol/N10.txt | BLOCKED |
| N11 | SKIP | argocd -> Internet 443 (Git and Helm repositories) (expected: allow) | 0 |  | not run: platform-argocd is not installed; the argocd namespace belongs to another deployment |
| N12 | PASS | logging -> Loki (log conduit) (expected: allow) | 0 | netpol/N12.txt | CONNECTED |
