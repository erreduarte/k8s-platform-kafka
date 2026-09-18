{{- define "schema-registry.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "schema-registry.fullname" -}}
{{- printf "%s-%s" .Release.Name (include "schema-registry.name" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "schema-registry.labels" -}}
app.kubernetes.io/name: {{ include "schema-registry.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/part-of: kafka
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
{{- end }}

{{- define "schema-registry.selectorLabels" -}}
app.kubernetes.io/name: {{ include "schema-registry.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
