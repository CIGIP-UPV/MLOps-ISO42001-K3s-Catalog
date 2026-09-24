# Informe de validación en laboratorio del catálogo AR-MLOps-ZDM

Validación del catálogo `MLOps-ISO42001-K3s-Catalog` (rama `lab-validation`, publicada como versión 2.0.0) en el clúster K3s del laboratorio, como aportación de datos reales al capítulo 7 de la tesis. Los tres criterios del capítulo se evalúan así:

- **Instanciabilidad:** instalación de los charts con `infrastructure/install.sh` (sección 4), pruebas de humo por chart y prueba de extremo a extremo de los flujos (sección 5).
- **Coherencia:** separación de niveles en nodos distintos, flujos de consolidación de datos y de propagación de versiones, y segmentación de red entre zonas (secciones 3, 4 y 5).
- **Trazabilidad:** consultas por las etiquetas `iso42001` de cada cláusula y componente (sección 6).

**Resumen de resultados en el laboratorio**

| Criterio | Resultado |
|---|---|
| Instalación | 27 charts desplegados (28 ejecuciones de Helm: cert-manager hace dos pasadas) en {{INSTALL_TOTAL}}, sin fallos; 3 charts omitidos por motivos del entorno |
| Pruebas de humo | 18 correctas, 0 fallidas y 3 no ejecutadas (Falco en el dispositivo edge, Argo CD y MongoDB, por el entorno) |
| Extremo a extremo | 16 de 16 tramos: simulador OPC UA, pasarela, ingesta validada, consolidación, entrenamiento, registro, propagación al edge, inferencia, métricas, deriva inducida, recomendación, reentrenamiento automático, nueva versión servida en el edge, registros en Loki e informes en Evidently |
| Segmentación de red | 12 correctas (incluido el control N00), 1 fallida y 1 no ejecutada; aplican NetworkPolicy 2 de los 3 nodos, y el fallo se debe a que el dispositivo edge no puede aplicarlas (kernel sin `ip_set_hash_ip`) |
| Trazabilidad | Las 19 cláusulas y 14 de los 15 componentes devuelven recursos; CMP-12 no tiene chart |

**Origen de los datos.** Todo dato de las secciones 1 a 6 procede de ejecuciones en el laboratorio con `docs/lab-validation/run-lab-validation.sh`, cuyas evidencias están en `docs/lab-validation/raw/<ejecución>/` (una línea por prueba en `results.jsonl`, con el comando). Lo que procede del clúster local de desarrollo (Docker Desktop, kind, arm64) se indica expresamente y está en `docs/lab-validation/local-evidence/`. Las ejecuciones se listan en el anexo. Antes de publicar, las direcciones IP públicas de los nodos se sustituyeron en las evidencias por `<ip-kb2>`, `<ip-worker1-kb2>` y `<ip-edgenode01>`; es el único cambio hecho a las salidas originales.
