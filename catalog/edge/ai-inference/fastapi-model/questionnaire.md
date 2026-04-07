# Deployment Questionnaire — FastAPI Model Server (Edge AI Inference)

Answer these questions before deploying the edge inference service. *(ISO/IEC 42001: B.6.1.2.2, B.6.1.3.4, B.6.2.6.1)*

---

## Section 1: Model Characteristics

**Q1. What type of AI model will be served?**

- [ ] LSTM / RNN (time-series prediction, e.g., predictive maintenance)
- [ ] CNN (image-based inspection)
- [ ] Classical ML (Random Forest, SVM, XGBoost)
- [ ] Anomaly detection (Isolation Forest, Autoencoder)
- [ ] Regression model

> This determines the expected input format, preprocessing steps, and resource requirements.

**Q2. What is the expected inference latency requirement?**

- [ ] < 100 ms — requires model optimisation (quantisation/pruning); benchmark before deployment
- [ ] 100–500 ms — standard CPU inference acceptable
- [ ] > 500 ms — no strict latency constraint; cloud model may be sufficient

**Q3. What is the input data shape?**

- Sequence length (for LSTM): _____ timesteps
- Features per timestep: _____ signals
- Batch size at inference: _____ (typically 1 for real-time)

---

## Section 2: Model Lifecycle & Versioning

**Q4. How will model artefacts be delivered to the edge?** *(B.6.1.3.4)*

- [ ] Baked into container image — simple, but requires image rebuild per model update
- [ ] Pulled from MinIO on startup — flexible; requires MinIO access from edge
- [ ] Mounted from PVC (pre-loaded from platform) — recommended for intermittent connectivity
- [ ] Pulled directly from MLflow model registry — requires stable platform connection

**Q5. What is the model promotion policy?** *(B.6.1.3.4)*

- [ ] Manual approval by data scientist + production manager before edge deployment
- [ ] Automatic if validation metrics exceed threshold (document threshold in MLflow)
- [ ] Pilot deployment on one machine before fleet rollout

> The promotion policy must be documented in the Deployment Plan stored in MinIO Document Store.

---

## Section 3: Observability & Compliance

**Q6. Which metrics should be exposed via `/metrics` for Prometheus?** *(B.6.1.2.2)*

- [ ] Inference request count
- [ ] Inference latency (p50, p95, p99)
- [ ] Prediction score distribution (to detect output drift)
- [ ] Error rate (failed inference requests)
- [ ] Model version currently loaded

**Q7. Should individual predictions be logged for audit purposes?** *(B.6.2.8.1)*

- [ ] Yes, all predictions — log input hash + prediction + timestamp to PostgreSQL
- [ ] Yes, anomaly predictions only — log only when score exceeds alert threshold
- [ ] No — metrics aggregation is sufficient

---

## Section 4: Hardware & Resource Constraints

**Q8. Does the edge node have a GPU?**

- [ ] Yes — configure `resources.limits.nvidia.com/gpu: 1` in the manifest
- [ ] No — CPU-only inference; consider ONNX Runtime for optimised CPU performance

**Q9. Available resources on the edge node for this service:**

- CPU: _____ cores available
- RAM: _____ GB available

> Minimum recommended: 0.5 CPU cores, 512 MB RAM for a lightweight LSTM model.

---

## Recommended Configuration Summary

```yaml
# fastapi-deployment.yaml — Key parameters to set based on answers above
env:
  - name: MODEL_PATH
    value: "/models/lstm_v1.onnx"   # Q4: path depends on delivery method
  - name: LOG_PREDICTIONS
    value: "true"                    # Q7: set to false if not logging
  - name: MODEL_VERSION
    value: "1.0.0"                   # Q5: must match MLflow registry version

resources:
  requests:
    cpu: "500m"
    memory: "512Mi"
  limits:
    cpu: "1000m"                     # Q9: adjust to available resources
    memory: "1Gi"

replicas: 1                          # Increase to 2 for high-availability edge
```
