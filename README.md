# OpenShift application networking and isolation demo

A small lab example for exposing a containerized service through an OpenShift Route while restricting pod ingress with a Kubernetes NetworkPolicy. This is a demo manifest set; review cluster policy, namespace labels, TLS requirements, and image policy before applying it in a real cluster.

## What it demonstrates
- Deployment and ClusterIP Service for an unprivileged web container
- OpenShift Route with edge TLS termination
- Default-deny ingress and a scoped allow rule for pods labelled `role=frontend`

## Apply in a disposable lab namespace
```sh
oc new-project network-demo
oc apply -f manifests/
oc get route web-demo
```
Only approved frontend-labelled pods in the same namespace should be able to reach the application pods on TCP 8080. NetworkPolicy enforcement depends on the cluster network plugin and policy configuration.
