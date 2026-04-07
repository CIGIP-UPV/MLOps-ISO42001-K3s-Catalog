{{/*
Expand the name of the chart.
*/}}
{{- define "enterprise-minio-overlay.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "enterprise-minio-overlay.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "enterprise-minio-overlay.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "enterprise-minio-overlay.labels" -}}
helm.sh/chart: {{ include "enterprise-minio-overlay.chart" . }}
{{ include "enterprise-minio-overlay.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
iso42001/tier: enterprise
{{- end }}

{{/*
Selector labels
*/}}
{{- define "enterprise-minio-overlay.selectorLabels" -}}
app.kubernetes.io/name: {{ include "enterprise-minio-overlay.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
