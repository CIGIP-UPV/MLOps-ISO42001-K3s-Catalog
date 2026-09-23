{{/*
Base name of every object: the release name (install.sh uses the chart name).
*/}}
{{- define "platform-evidently.fullname" -}}
{{- .Release.Name | trunc 40 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels, including the ISO/IEC 42001 traceability labels.
*/}}
{{- define "platform-evidently.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: iso42001-ai-system
{{- with .Values.iso42001Labels }}
{{ toYaml . }}
{{- end }}
{{- end }}

{{- define "platform-evidently.selectorLabels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: ui
{{- end }}

{{/*
Environment shared by the extract and recommend steps of the drift check.
*/}}
{{- define "platform-evidently.driftEnv" -}}
- { name: HOME, value: /tmp }
- { name: WORK_DIR, value: /work }
- { name: GIT_PYTHON_REFRESH, value: quiet }
- { name: MLFLOW_TRACKING_URI, value: {{ .Values.driftCheck.mlflowTrackingUri | quote }} }
- { name: MODEL_NAME, value: {{ .Values.driftCheck.modelName | quote }} }
- { name: MODEL_ALIAS, value: {{ .Values.driftCheck.alias | quote }} }
- { name: CURRENT_WINDOW, value: {{ .Values.driftCheck.currentWindow | quote }} }
- { name: BUCKET, value: {{ .Values.driftCheck.bucket | quote }} }
- { name: MIN_CURRENT_ROWS, value: {{ .Values.driftCheck.minCurrentRows | quote }} }
- { name: DB_HOST, value: {{ .Values.driftCheck.dataStock.host | quote }} }
- { name: DB_PORT, value: {{ .Values.driftCheck.dataStock.port | quote }} }
- { name: DB_NAME, value: {{ .Values.driftCheck.dataStock.database | quote }} }
- { name: DB_USER, value: {{ .Values.driftCheck.dataStock.user | quote }} }
- name: DB_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ .Values.driftCheck.dataStock.existingSecret }}
      key: {{ .Values.driftCheck.dataStock.passwordKey }}
{{- end }}
