{{/*
Base name of every object (release name; install.sh uses the chart name).
*/}}
{{- define "edge-opc-ua-gateway.fullname" -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels, including the ISO/IEC 42001 traceability labels.
*/}}
{{- define "edge-opc-ua-gateway.labels" -}}
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

{{- define "edge-opc-ua-gateway.selectorLabels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
