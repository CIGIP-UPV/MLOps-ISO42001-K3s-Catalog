{{/*
Expand the name of the chart.
*/}}
{{- define "platform-timescaledb.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "platform-timescaledb.fullname" -}}
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
{{- define "platform-timescaledb.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels, including the ISO/IEC 42001 traceability labels.
*/}}
{{- define "platform-timescaledb.labels" -}}
helm.sh/chart: {{ include "platform-timescaledb.chart" . }}
{{ include "platform-timescaledb.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: iso42001-ai-system
{{- with .Values.iso42001Labels }}
{{ toYaml . }}
{{- end }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "platform-timescaledb.selectorLabels" -}}
app.kubernetes.io/name: {{ include "platform-timescaledb.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
