# OpenShift application networking and isolation

This lab example deploys a small HTTP workload, exposes it through an OpenShift Route with edge TLS termination, and applies a Kubernetes NetworkPolicy that limits pod ingress to selected frontend pods. It demonstrates how service discovery, north-south exposure, and pod-level segmentation are separate concerns.

## Architecture

- **Deployment:** two replicas labelled `app=web-demo`, using an unprivileged NGINX image on port 8080.
- **Service:** stable in-cluster endpoint on port 8080 targeting the named container port.
- **Route:** exposes the Service through the OpenShift router with edge TLS termination.
- **NetworkPolicy:** selects only `app=web-demo` pods and permits TCP/8080 ingress from pods labelled `role=frontend` in the same namespace.

The policy does not create a frontend workload. Without a matching source pod, the selected web pods' ingress is denied for traffic governed by NetworkPolicy. The policy is ingress-only; egress remains unaffected by this policy unless another policy selects the pods.

## Prerequisites

- An OpenShift cluster or disposable Kubernetes lab whose CNI enforces NetworkPolicy.
- `oc` CLI authenticated to the intended lab cluster.
- Permission to create a project/namespace, Deployment, Service, Route, and NetworkPolicy.
- Ability to pull the example container image.

## Safe lab run

Review all YAML before applying. In a disposable lab:

```bash
oc new-project network-demo
oc apply -f manifests/
oc get deployment,service,networkpolicy,route
oc rollout status deployment/web-demo
oc get route web-demo
```

Create a test frontend pod with label `role=frontend` to verify the allowed path; use a controlled test image already approved in your environment. Test both allowed and disallowed ingress from separate pods. Do not assume a successful Route request proves NetworkPolicy enforcement.

Clean up only the dedicated lab namespace after confirming it contains no other work:

```bash
oc delete project network-demo
```

## Security and TLS notes

Edge termination encrypts client-to-router traffic; traffic from the router to the Service is not encrypted by this Route configuration. Use re-encrypt or passthrough where the threat model and application support require end-to-end encryption. Review router policy, certificate management, image provenance, resource requests/limits, service account permissions, and pod security settings before adapting the manifests.

## Validation

Useful checks include `oc apply --dry-run=server -f manifests/`, `oc describe networkpolicy web-demo-ingress`, and connectivity tests from labelled and unlabelled pods. A server-side dry run requires cluster access and does not prove actual dataplane enforcement. No cluster test result is claimed; enforcement depends on the installed network plugin and cluster configuration.

## Limitations

This is a demonstration, not a hardened application deployment. It lacks resource limits, probes, egress controls, namespace-wide default deny, DNS-specific policy, trusted image pinning by digest, and an automated integration test. Evaluate those requirements before use.
