apiVersion: v1
kind: Service
metadata:
  name: svcpnh
spec:
  selector:
    app: app1
  type: NodePort
  ports:
  - name: port1
    port: 80
    targetPort: 8000
    nodePort: 31080
