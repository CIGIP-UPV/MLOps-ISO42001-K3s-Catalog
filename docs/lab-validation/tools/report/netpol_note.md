
**Lectura de los resultados.**

- `kb2` y `worker1-kb2` aplican NetworkPolicy; `edgenode01` no. Su controlador (kube-router, integrado en K3s) falla en bucle con `ipset restore: set type not supported`, porque el kernel `5.15.148-tegra` de JetPack no incluye el módulo `ip_set_hash_ip` (`raw/diag-ubuntu-20260924T113108.txt`).
- Las denegaciones hacia servicios de plataforma (N04, N05 y N10) y todos los conductos permitidos funcionan.
- N08 comprueba la denegación de salida hacia Internet desde `mlops`.
- N13 comprueba una regla de salida por sí sola: el destino está en el dispositivo edge, que no filtra, y aun así la conexión se bloquea en origen.
- N06 falla porque su protección depende de la regla de entrada del pod de destino, que corre en el dispositivo edge.
- N11 no se ejecutó porque el namespace `argocd` pertenece a otro despliegue.

**Historia de las ejecuciones de red.** La segmentación solo pudo medirse tras varios ajustes, todos con evidencia:

1. **Controlador desactivado.** K3s tenía `disable-network-policy: true`. El script lo quitó y reinició `k3s` en el primer intento (PREP-04 correcto en `lab-20260924T075022`; en `lab-20260924T081803` ya no estaba, según `state/enable-network-policy.txt`), pero los agentes de `worker1-kb2` y `edgenode01` necesitaban también reiniciarse (canarios de `lab-20260924T081803` y `lab-20260924T092125`).
2. **Clientes en un nodo que aplica políticas.** En `lab-20260924T093809` los clientes ya iban a un nodo que aplica políticas, pero N08 dio CONNECTED: el controlador tarda unos segundos en incluir un pod recién creado en sus reglas, y el cliente conectaba antes.
3. **Espera de sincronización.** Con la espera de 15 s (commit a3b8999), N08 queda bloqueada en la ejecución de referencia.

Las ejecuciones anteriores se conservan como historial.
