# demo-kubernetes

# lab1.this demo will create K8S Cluster use Ansible.

### prepare 3 server
- ansible server
- 1 k8s master server
- 1 k8s worker server

copy SSH key file to ansible server (use for ssh from Ansible to k8s server)
```
scp -i sshkey.pem sshkey.pem azureuser@20.193.149.25:/home/azureuser/.ssh/
```

on ansible server, move to .ssh folder then convert ssh key 
```
cd ~/.ssh
sudo apt install openssl
openssl rsa -in sshkey.pem -out id_rsa
```

On 2 k8s server:
```
sudo swapoff -a
sudo sed -i '/swap/ s/^\(.*\)$/#\1/g' /etc/fstab
hostnamectl set-hostname master     // only on master host
hostnamectl set-hostname worker1    // only on worker host
```
open Security Group Port 6443.

### use Ansible to install containerd,  kubeadm, kubelet and kubectl

at first, on ansible server create hosts file. (10.0.1.4, 10.0.2.4 is private IP address of 2 servers)
```
10.0.2.4 kubernetes_role="master"  ansible_user=azureuser
10.0.1.4 kubernetes_role="node"  ansible_user=azureuser
```

then create playbook.yml
```yml
- hosts: all
  become: true
  become_method: sudo
  become_user: root
  vars:
    kubernetes_allow_pods_on_master: true
  pre_tasks:
    - name: Create containerd config file
      file:
        path: "/etc/modules-load.d/containerd.conf"
        state: "touch"

    - name: Add conf for containerd
      blockinfile:
        path: "/etc/modules-load.d/containerd.conf"
        block: |
              overlay
              br_netfilter

    - name: modprobe
      shell: |
              sudo modprobe overlay
              sudo modprobe br_netfilter

    - name: Set system configurations for Kubernetes networking
      file:
        path: "/etc/sysctl.d/99-kubernetes-cri.conf"
        state: "touch"

    - name: Add conf for containerd
      blockinfile:
        path: "/etc/sysctl.d/99-kubernetes-cri.conf"
        block: |
               net.bridge.bridge-nf-call-iptables = 1
               net.ipv4.ip_forward = 1
               net.bridge.bridge-nf-call-ip6tables = 1

    - name: Apply new settings
      command: sudo sysctl --system
    - name: Swap off
      shell: |
              sudo swapoff -a
              sudo sed -i '/swap/ s/^\(.*\)$/#\1/g' /etc/fstab

  roles:
    - geerlingguy.containerd
    - geerlingguy.kubernetes
```

in this script, we use 2 roles: `geerlingguy.containerd` and `geerlingguy.kubernetes`. 
```
ansible-galaxy install geerlingguy.containerd
ansible-galaxy install geerlingguy.kubernetes
```

after installed 2 roles on galaxy, then  run playbook script
```
ansible-playbook -i hosts playbook.yml
```

### create cluster
run below command to create cluster (with 10.0.2.4 is priavate IP address of master server).
```
sudo kubeadm init --pod-network-cidr=10.244.0.0/16 --ignore-preflight-errors=all  --apiserver-advertise-address=10.0.2.4
```
this command will output command that allow worker to join cluster. Copy that command then run on worker server.
```
sudo kubeadm join 10.0.2.4:6443 --token csxlf3.ngqaglgelx6nxnct     --discovery-token-ca-cert-hash sha256:f0b5b568a09266f56823a369c0f551caab6d62bdf6277a00f98b1bf653db3119
```

on master server, if you don't want to type sudo many time then create alias `alias kubectl=sudo kubectl`, or copy kubectl conf to azureubuntu user:
```
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

finally,  confirm created node by using command `kubectl get node -o wide` :
```
NAME      STATUS   ROLES                  AGE   VERSION    INTERNAL-IP   EXTERNAL-IP   OS-IMAGE             KERNEL-VERSION      CONTAINER-RUNTIME
master    Ready    control-plane,master   41h   v1.20.15   10.0.2.4      <none>        Ubuntu 20.04.5 LTS   5.15.0-1023-azure   containerd://1.6.10
worker1   Ready    <none>                 41h   v1.20.15   10.0.1.4      <none>        Ubuntu 20.04.5 LTS   5.15.0-1023-azure   containerd://1.6.10
```

and check list pods with `get pod -o wide -A`:
```
NAMESPACE      NAME                             READY   STATUS    RESTARTS   AGE   IP           NODE      NOMINATED NODE   READINESS GATES
kube-flannel   kube-flannel-ds-42vhc            1/1     Running   1          40h   10.0.1.4     worker1   <none>           <none>
kube-flannel   kube-flannel-ds-mkgc7            1/1     Running   2          40h   10.0.2.4     master    <none>           <none>
kube-system    coredns-74ff55c5b-gnkjt          1/1     Running   2          40h   10.244.0.6   master    <none>           <none>
kube-system    coredns-74ff55c5b-qb4q7          1/1     Running   2          40h   10.244.0.7   master    <none>           <none>
kube-system    etcd-master                      1/1     Running   2          40h   10.0.2.4     master    <none>           <none>
kube-system    kube-apiserver-master            1/1     Running   2          40h   10.0.2.4     master    <none>           <none>
kube-system    kube-controller-manager-master   1/1     Running   2          40h   10.0.2.4     master    <none>           <none>
kube-system    kube-proxy-hjk2w                 1/1     Running   2          40h   10.0.2.4     master    <none>           <none>
kube-system    kube-proxy-p5mz9                 1/1     Running   1          40h   10.0.1.4     worker1   <none>           <none>
kube-system    kube-scheduler-master            1/1     Running   2          40h   10.0.2.4     master    <none>           <none>
```

 if any Pod CoreDNS is pending or faulty, then try to run:
```
kubectl apply -f https://raw.githubusercontent.com/flannel-io/flannel/master/Documentation/kube-flannel.yml
```

some usefull commands:
```
kubectl config view
kubectl get namespace                   //k8s manage resource by separate namespace
kubectl get cm -o yaml -n kube-system kubeadm-config    //descibe cluster spec, and its card network
kubectl get pod -o wide -A              //check pods created and those namespace
kubectl create namespace pythonstack    //create new namespace named `pythonstack`
kubectl get namespace                   //print namespaces list
```


## lab2.create new service on k8s cluster
this service has code in gitlab. so first, login to docker registry on both Master and Worker:
```
sudo docker login -u git-deploy-token -p XXX registry.gitlab.com/levtienbk56/pythonapp:latest
```

on **Master** server, create 2 files:
- `pypod.py`: create a Pod pythonapp that run a python app, on port 8000
```python
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
```
- `svcpy.py`: create service on port 80, as a LoadBalance between NodePort 31080 and Pod 8000 (client who access App through NodePort 31080)
```python
apiVersion: v1
kind: Service
metadata:
  name: svcpnh
spec:
  selector:
    app: app1   # must have same name as label app1 in Pod script. Service use this selector to direct request to Pod
  type: NodePort
  ports:
  - name: port1
    port: 80
    targetPort: 8000
    nodePort: 31080
```

run `pypod.py` script to create pod `kubectl apply -f pypod.py`
```
azureuser@master:~/pythonapp$ kubectl get pod -o wide -A
NAMESPACE      NAME                             READY   STATUS    RESTARTS   AGE   IP           NODE      NOMINATED NODE   READINESS GATES
default        python1                          1/1     Running   0          27s   10.244.1.2   worker1   <none>           <none>
kube-flannel   kube-flannel-ds-42vhc            1/1     Running   1          42h   10.0.1.4     worker1   <none>           <none>
kube-flannel   kube-flannel-ds-mkgc7            1/1     Running   2          42h   10.0.2.4     master    <none>           <none>
kube-system    coredns-74ff55c5b-gnkjt          1/1     Running   2          42h   10.244.0.6   master    <none>           <none>
kube-system    coredns-74ff55c5b-qb4q7          1/1     Running   2          42h   10.244.0.7   master    <none>           <none>
kube-system    etcd-master                      1/1     Running   2          42h   10.0.2.4     master    <none>           <none>
kube-system    kube-apiserver-master            1/1     Running   2          42h   10.0.2.4     master    <none>           <none>
kube-system    kube-controller-manager-master   1/1     Running   2          42h   10.0.2.4     master    <none>           <none>
kube-system    kube-proxy-hjk2w                 1/1     Running   2          42h   10.0.2.4     master    <none>           <none>
kube-system    kube-proxy-p5mz9                 1/1     Running   1          42h   10.0.1.4     worker1   <none>           <none>
kube-system    kube-scheduler-master            1/1     Running   2          42h   10.0.2.4     master    <none>           <none>
```

run `svcpy.py` script to create service `kubectl apply -f svcpy.py`
```
azureuser@master:~/pythonapp$ kubectl get svc -o wide
NAME         TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)        AGE   SELECTOR
kubernetes   ClusterIP   10.96.0.1       <none>        443/TCP        42h   <none>
svcpnh       NodePort    10.98.254.120   <none>        80:31080/TCP   37s   app=app1
```

try access app from internet (need open port 31080)
```
azureuser@master:~/pythonapp$ curl 20.193.137.159:31080
You access this web site version 2: 999 times.
```

you can access into container inside Pod. If Pod have many container, then specify name of container with `-c`
```
azureuser@master:~/pythonapp$ kubectl exec -it python1 -c py1 -- /bin/sh
/code #
```
Log of pod can check by using command `kubectl logs python1`.
```
 * Serving Flask app "app" (lazy loading)
 * Environment: production
   WARNING: This is a development server. Do not use it in a production deployment.
   Use a production WSGI server instead.
 * Debug mode: on
 * Running on http://0.0.0.0:8000/ (Press CTRL+C to quit)
 * Restarting with stat
 * Debugger is active!
 * Debugger PIN: 705-776-349
10.244.1.1 - - [01/Dec/2022 09:51:41] "GET / HTTP/1.1" 200 -
10.244.1.1 - - [01/Dec/2022 09:52:04] "GET / HTTP/1.1" 200 -
10.244.1.1 - - [01/Dec/2022 09:55:06] "GET / HTTP/1.1" 200 -
10.244.1.1 - - [01/Dec/2022 09:55:06] "GET /favicon.ico HTTP/1.1" 404 -
10.244.1.1 - - [01/Dec/2022 09:55:23] "GET / HTTP/1.1" 200 -
10.244.1.1 - - [01/Dec/2022 11:17:50] "GET / HTTP/1.1" 200 -
```

