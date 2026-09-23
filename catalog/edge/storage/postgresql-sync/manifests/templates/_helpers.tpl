{{/*
Expand the name of the chart.
*/}}
{{- define "edge-postgresql-sync.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "edge-postgresql-sync.fullname" -}}
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
{{- define "edge-postgresql-sync.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels, including the ISO/IEC 42001 traceability labels.
*/}}
{{- define "edge-postgresql-sync.labels" -}}
helm.sh/chart: {{ include "edge-postgresql-sync.chart" . }}
app.kubernetes.io/name: {{ include "edge-postgresql-sync.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: iso42001-ai-system
{{- with .Values.iso42001Labels }}
{{ toYaml . }}
{{- end }}
{{- end }}

{{/*
Space-separated list of the tables to consolidate.
*/}}
{{- define "edge-postgresql-sync.tables" -}}
{{- $t := list }}
{{- if .Values.tables.sensorFeatures }}{{ $t = append $t "sensor_features" }}{{ end }}
{{- if .Values.tables.predictions }}{{ $t = append $t "predictions" }}{{ end }}
{{- join " " $t }}
{{- end }}
