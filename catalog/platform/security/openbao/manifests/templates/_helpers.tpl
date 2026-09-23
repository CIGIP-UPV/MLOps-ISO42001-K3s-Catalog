{{/*
Common labels, including the ISO/IEC 42001 traceability labels.
*/}}
{{- define "platform-openbao.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
app.kubernetes.io/part-of: iso42001-ai-system
{{- with .Values.iso42001Labels }}
{{ toYaml . }}
{{- end }}
{{- end -}}
