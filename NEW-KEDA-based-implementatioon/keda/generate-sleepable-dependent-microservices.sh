#!/bin/bash
mkdir -p keda-scaledobjects

BACKENDS=("adservice" "cartservice" "checkoutservice" "currencyservice" "emailservice" "loadgenerator" "paymentservice" "productcatalogservice" "recommendationservice" "redis-cart" "shippingservice")

for svc in "${BACKENDS[@]}"; do
cat <<EOF > keda-scaledobjects/${svc}-scaledobject.yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: ${svc}-scaledobject
spec:
  scaleTargetRef:
    name: ${svc}
  pollingInterval: 15
  cooldownPeriod: 30
  minReplicaCount: 0
  maxReplicaCount: 1
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus-kube-prometheus-prometheus.monitoring.svc.cluster.local:9090
      metricName: frontend_up
      query: kube_deployment_status_replicas{deployment="frontend",namespace="default"} > 0
      threshold: '1'
EOF
echo "Generated ScaledObject for ${svc} -> ./keda-scaledobjects/${svc}-scaledobject.yaml"
done
