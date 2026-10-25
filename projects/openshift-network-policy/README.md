# OpenShift application networking and isolation demo

Lab example exposing a containerized service through an OpenShift Route while restricting pod ingress with Kubernetes NetworkPolicy. Review cluster policy, namespace labels, TLS requirements, and image policy before applying in a real cluster.

## Apply in a disposable lab namespace
```sh
oc new-project network-demo
oc apply -f manifests/
oc get route web-demo
```
NetworkPolicy enforcement depends on the cluster network plugin and policy configuration.
