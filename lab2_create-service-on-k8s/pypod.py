apiVersion: v1
kind: Pod
metadata:
  name: python1
  labels:
    app: app1
spec:
  containers:
  - name: py1
    image: registry.gitlab.com/levtienbk56/pythonapp:latest
    resources:
      limits:
        memory: "128Mi"
        cpu: "100m"
    ports:
    - containerPort: 8000
