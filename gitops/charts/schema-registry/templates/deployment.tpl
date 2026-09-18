apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "schema-registry.fullname" . }}
  labels:
    {{- include "schema-registry.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      {{- include "schema-registry.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "schema-registry.selectorLabels" . | nindent 8 }}
    spec:
      containers:
        - name: schema-registry
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: http
              containerPort: {{ .Values.service.port }}
              protocol: TCP
          env:
            - name: SCHEMA_REGISTRY_HOST_NAME
              value: {{ include "schema-registry.fullname" . | quote }}
            - name: SCHEMA_REGISTRY_LISTENERS
              value: http://0.0.0.0:{{ .Values.service.port }}
            - name: SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS
              value: {{ .Values.kafka.bootstrapServers | quote }}
            - name: SCHEMA_REGISTRY_KAFKASTORE_TOPIC
              value: {{ .Values.kafka.topic | quote }}
            - name: SCHEMA_REGISTRY_KAFKASTORE_TOPIC_REPLICATION_FACTOR
              value: {{ .Values.kafka.topicReplicationFactor | quote }}
            - name: SCHEMA_REGISTRY_KAFKASTORE_SECURITY_PROTOCOL
              value: {{ .Values.kafka.securityProtocol | quote }}
            - name: SCHEMA_REGISTRY_KAFKASTORE_SASL_MECHANISM
              value: {{ .Values.kafka.saslMechanism | quote }}
            - name: SCHEMA_REGISTRY_KAFKASTORE_SASL_JAAS_CONFIG
              valueFrom:
                secretKeyRef:
                  name: {{ .Values.kafka.credentialsSecretName }}
                  key: {{ .Values.kafka.credentialsSecretKey }}
          readinessProbe:
            httpGet:
              path: /subjects
              port: http
            initialDelaySeconds: {{ .Values.readinessProbe.initialDelaySeconds }}
            periodSeconds: {{ .Values.readinessProbe.periodSeconds }}
            timeoutSeconds: {{ .Values.readinessProbe.timeoutSeconds }}
            failureThreshold: {{ .Values.readinessProbe.failureThreshold }}
          livenessProbe:
            httpGet:
              path: /subjects
              port: http
            initialDelaySeconds: {{ .Values.livenessProbe.initialDelaySeconds }}
            periodSeconds: {{ .Values.livenessProbe.periodSeconds }}
            timeoutSeconds: {{ .Values.livenessProbe.timeoutSeconds }}
            failureThreshold: {{ .Values.livenessProbe.failureThreshold }}
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
