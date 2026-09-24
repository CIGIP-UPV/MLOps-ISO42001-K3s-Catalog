{{/*
Expand the name of the chart.
*/}}
{{- define "enterprise-feedback-interface.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "enterprise-feedback-interface.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 52 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 52 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 52 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "enterprise-feedback-interface.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels, including the ISO/IEC 42001 traceability labels.
*/}}
{{- define "enterprise-feedback-interface.labels" -}}
helm.sh/chart: {{ include "enterprise-feedback-interface.chart" . }}
app.kubernetes.io/name: {{ include "enterprise-feedback-interface.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: iso42001-ai-system
{{- with .Values.iso42001Labels }}
{{ toYaml . }}
{{- end }}
{{- end }}

{{/*
Selector labels.
*/}}
{{- define "enterprise-feedback-interface.selectorLabels" -}}
app.kubernetes.io/name: {{ include "enterprise-feedback-interface.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
