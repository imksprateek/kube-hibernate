#!/bin/bash

# Set your frontend/external LB IP
LOADBALANCER_IP="34.59.95.223"   # replace with your actual LB IP

# Directory to store the generated YAML files
OUTPUT_DIR="./keda-scaledobjects"
mkdir -p $OUTPUT_DIR

# Loop over all sleepable=true deployments in default namespace
for deploy in $(kubectl get deploy -n default -l sleepable=true -o jsonpath='{.items[*].metadata.name}'); do
  # Get the first port from the corresponding service
  port=$(kubectl get svc $deploy -n default -o jsonpath='{.spec.ports[0].port}')

  # File name for this deployment's HTTPScaledObject
  file="$OUTPUT_DIR/${deploy}-scaledobject.yaml"

  # Create YAML file
  cat <<EOF > $file
apiVersion: http.keda.sh/v1alpha1
kind: HTTPScaledObject
metadata:
  name: ${deploy}-scaledobject
  namespace: default
spec:
  hosts:
    - "$LOADBALANCER_IP"
  scaleTargetRef:
    name: ${deploy}
    kind: Deployment
    apiVersion: apps/v1
    service: ${deploy}
    port: $port
  replicas:
    min: 0
    max: 10
  targetPendingRequests: 10
EOF

  echo "Generated $file"
done

echo "All YAML files are generated in $OUTPUT_DIR. You can inspect them before applying."
