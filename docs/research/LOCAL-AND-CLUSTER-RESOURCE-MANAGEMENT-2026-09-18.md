# Local and cluster resource management for harness instances

Date: 2026-09-18. Requested by the owner, who asked for local resource
detection and management of the harness instances that run solutioning
nodes, for the same in the cloud with capacity that grows within a client's
budget, for a front end that system administrators and client
administrators would use, and for research on which infrastructure shape
should carry thousands of solutioning nodes. This record reports what the
primary documentation of each system says, what this machine showed, and
what Loop Engine holds on this date. It is research. It decides nothing.
The owner decides.

Every source in this record was read on 2026-09-18 through direct fetches
of documentation pages. Each subsection links the pages it relies on, and
the last section lists every address with the date read and the outcome of
the fetch. A fact that could not be confirmed from a fetched page is marked
unverified. Every figure is labeled as a documented limit, a figure measured
on this machine, or an estimate.

## Words used in this record

- A solutioning node is one node of the solutioning space: one discrete
  cognitive or act step Loop node. The complete behavioral explanation of
  that phrase is in [ASTRA.md](../../ASTRA.md#complete-behavioral-explanation)
  and is not repeated here.
- A harness instance is the process or container that runs one solutioning
  node: the custom in-process Practitioner, or an external coding harness
  such as Codex, OpenCode, or Pi, each a separate process.
- A Kubernetes node is a machine in a cluster. This record writes
  "Kubernetes node" or "machine" for that meaning. It never uses the bare
  word "node" for a machine.
- A worker pool is a set of long-lived worker processes or worker pods,
  each hosting several solutioning nodes at once.
- Observed means read from a fetched page, from the working tree, or from
  this machine. Inferred means derived from observed facts by arithmetic or
  reasoning. Assumed means a working assumption that no source supports
  yet. Missing means a fact that was looked for and not found.

## What the owner asked

1. Local: a supervisor that keeps the number of live solutioning nodes
   within what the machine can carry, detects stalled nodes and clears
   them, can pause or hibernate a node that is doing iterative solutioning
   and taking too much memory and restart it later, with logging and
   tracking.
2. Cloud: the same, plus the ability to spin up more resources within a
   client's budget and limits.
3. Front end: how system administrators and client administrators would
   manage this.
4. Infrastructure: one Kubernetes pod per solutioning node, many
   solutioning nodes per pod, thousands of nodes, the overhead of each
   shape, and which existing distributed processing systems already solve
   this.

## What Loop Engine holds on this date

Observed in the working tree of `/home/username/loop-engine` on
2026-09-18. Nothing in this table is a claim that the piece has been used
in a live cluster.

| Piece | Where | State |
|---|---|---|
| Worker image | `ghcr.io/alisonjieli-png/loop-engine`, first published from commit `855ab32` (the [packaging guide](../guides/packaging-tiers-and-hosted-service.md) records the digest) | Published; no hosted endpoint operated |
| Kubernetes manifests | `examples/28_containerized_worker/k8s/`: a Deployment (`loop-engine-worker`, requests `500m` and `512Mi`, limits `2` and `2Gi`, a readiness probe on `/health` every 10 seconds) and a Job (`backoffLimit: 0`, `ttlSecondsAfterFinished: 86400`, requests `250m` and `256Mi`, limits `1` and `1Gi`, an `emptyDir` work volume) | Validated offline by example 28; not deployed |
| Studio | [Studio runtime views](../guides/studio-runtime-views.md): a local, read-only interface that accepts GET requests only and shows the runtime inventory, spawned tasks, external harness summaries, approvals, context artifacts, compactions, and skill loads | Published; shows no machine resource state and offers no write action |
| Hosted service surface | `src/loop_engine/core/service_api.py`: tenants whose keys are stored as digests, the endpoints `health`, `conform`, `evaluate`, `usage`, `memory_write`, and `memory_read`, and a metering ledger over the units `verified_completion`, `avoided_model_call`, `optimize_hour`, and `judgment_depth`; `usage` returns a `tenant_usage/v1` record with totals | Published and checked offline; no budget field, no quota field |
| Concurrency contracts | `src/loop_engine/scheduling.py` (`ConcurrencyContract`, `SchedulingConfiguration` with `maximum_concurrency`, the scheduling patterns) and `src/loop_engine/parallel_runner.py` (a semaphore bounds in-process branches) | Published; bounds in-process branches, not operating-system processes |
| Measured capacity | `src/loop_engine/core/runtime_capacity.py`: measured memory and disk with the basis for each figure; declared ceilings are refused | Published |
| Local supervisor | `src/loop_engine/core/local_resources.py`: committed on this date as `e4b543b` by a concurrent session while this record was being written (the changelog entry names roadmap step S-2.22, states `offline_verified`, and reports eight mutants killed). It reads `/proc/meminfo`, `/proc/pressure`, the control group `memory.max` and `memory.current`, the load average, and the processor count into a `resource_snapshot/v1` with unknown kept distinct from zero; keeps an `instance_ledger/v1` with the states `running`, `paused`, `hibernated`, `stopped`, and `stalled`, heartbeats, sampled memory, and an append-only event log with a reason per transition; admits a new instance within a ceiling (a declared `max_instances`, otherwise the processor count) and above a memory reserve (`memory_reserve_fraction` 0.2 by default); marks an instance stalled after `stall_after_seconds` (300 by default); pauses the largest running instance when available memory falls below the reserve or memory pressure `avg10` exceeds `pressure_pause_avg10` (20 by default); resumes paused instances when available memory recovers above `resume_reserve_fraction` (0.3 by default); and sends every operating-system effect through an injected controller (`SignalController` sends `SIGSTOP`, `SIGCONT`, and `SIGTERM` to owned process identifiers only) | Committed in `e4b543b`. The ledger lives in memory. The `hibernated` state and the `container` instance kind are declared, but no transition, controller action, or container controller exists for them |
| Roadmap steps | `docs/roadmap/roadmap.yaml`: S-2.22 (local resource detection and a supervisor) `offline_verified`; S-2.23 (cluster placement decision, one pod per node against a worker pool that hosts many nodes) `proposed`; S-4.8 (cloud capacity within a client budget, quotas, and spin-up policy) `proposed`; S-4.9 (administrator surfaces for system and client administrators) `proposed` | Recorded |
| Harness commands on this machine | `opencode`, `codex`, and `pi` are installed; `docker` and `systemd-run` (systemd 259) are installed; `criu`, `runsc`, `kata-runtime`, `firecracker`, and `kubectl` are not installed | Observed on this machine |

The event vocabulary that Studio maps runtime observations onto includes
`loop.paused` and `loop.resumed` (observed in the Studio guide). This
record did not verify what triggers those events today.

## 1. Kubernetes facts

All pages in this section are on kubernetes.io unless stated otherwise,
and all were read on 2026-09-18.

### Documented limits for large clusters

The [considerations for large clusters page](https://kubernetes.io/docs/setup/best-practices/cluster-large/)
states: "Kubernetes v1.37 supports clusters with up to 5,000 nodes. More
specifically, Kubernetes is designed to accommodate configurations that
meet all of the following criteria: No more than 110 pods per node; No more
than 5,000 nodes; No more than 150,000 total pods; No more than 300,000
total containers" (every "node" in that quotation is a Kubernetes node).
The same page advises one or two control plane instances
per failure zone, scaled vertically first, and notes that some addons scale
vertically (one replica per cluster or zone, whose requests and limits must
grow with the cluster) while others scale horizontally or run one copy per
Kubernetes node.

Inferred from those limits: three thousand solutioning nodes that each run
as their own pod at the same time need at least 28 Kubernetes nodes
(3,000 divided by 110, rounded up), before any headroom for the pods that
the cluster itself runs on each machine. The cluster-wide ceiling of
150,000 pods is fifty times that population.

The Kubernetes scalability special interest group publishes a
[pod startup latency service level objective](https://github.com/kubernetes/community/blob/master/sig-scalability/slos/pod_startup_latency.md)
(on github.com, not kubernetes.io): "Startup latency of schedulable
stateless pods, excluding time to pull images and run init containers,
measured from pod creation timestamp to when all its containers are
reported as started and observed via watch, measured as 99th percentile
over last 5 minutes", with the threshold "In default Kubernetes
installation, 99th percentile per cluster-day <= 5s". This is the
documented scheduling and start cost of the one-pod-per-node shape; it
excludes image pulls.

### Pod overhead and the RuntimeClass overhead field

The [pod overhead page](https://kubernetes.io/docs/concepts/scheduling-eviction/pod-overhead/)
is marked stable since Kubernetes v1.24. Overhead is declared on a
`RuntimeClass` through its `overhead` field; the page's example is a
`RuntimeClass` named `kata-fc` with `overhead.podFixed.memory: "120Mi"`
and `overhead.podFixed.cpu: "250m"`, described as the overhead of the
virtual machine and guest operating system that the Kata Containers with
Firecracker runtime adds per pod. "In Kubernetes, the Pod's overhead is set
at admission time according to the overhead associated with the Pod's
RuntimeClass." The scheduler adds the overhead to the sum of container
requests (the example needs "2250m CPU and 320MiB" for containers that
request 2000m and 200MiB), and "the kubelet will include the Pod overhead
when sizing the Pod cgroup, and when carrying out Pod eviction ranking".
The 120Mi and 250m values are the documentation's example for a virtual
machine runtime, not a measurement made for this record.

The [RuntimeClass page](https://kubernetes.io/docs/concepts/containers/runtime-class/)
is marked stable since Kubernetes v1.20. Handlers are configured in the
container runtime: under `[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.${HANDLER_NAME}]`
for containerd and under `[crio.runtime.runtimes.${HANDLER_NAME}]` for
CRI-O. A sandboxed runtime such as gVisor or Kata Containers is selected
per pod through this object.

### ResourceQuota and LimitRange for per-tenant limits

The [resource quotas page](https://kubernetes.io/docs/concepts/policy/resource-quotas/)
states: "A resource quota, defined by a ResourceQuota object, provides
constraints that limit aggregate resource consumption per namespace." It
can also cap the number of objects of one kind in the namespace and the
total infrastructure resources those objects consume.
The compute fields are `requests.cpu`, `requests.memory`, `limits.cpu`,
and `limits.memory`, each summed "across all pods in a non-terminal
state". Object counts such as `pods` and `count/jobs.batch` can be capped.
Scopes include `PriorityClass`, so a quota can be tied to a priority level.
"If creating or updating a resource violates a quota constraint, the
control plane rejects that request with HTTP status code 403 Forbidden."
And: "If quotas are enabled in a namespace for resource such as cpu and
memory, users must specify requests or limits for those values when they
define a Pod; otherwise, the quota system may reject pod creation."

The [limit ranges page](https://kubernetes.io/docs/concepts/policy/limit-range/)
states that a LimitRange can "Enforce minimum and maximum compute resources
usage per Pod or Container in a namespace", "Enforce a ratio between
request and limit for a resource in a namespace", and "Set default
request/limit for compute resources in a namespace and automatically inject
them to Containers at runtime". It applies "whenever there is at least one
LimitRange object in that namespace", and a violation fails with HTTP 403
Forbidden.

Together these two objects are the per-tenant boundary that Kubernetes
itself offers: one namespace per tenant, a ResourceQuota for the sum, and a
LimitRange for the per-container default and maximum.

### Jobs for many tasks

The [Job field reference](https://kubernetes.io/docs/reference/kubernetes-api/workload-resources/job-v1/)
defines `parallelism` as "the maximum desired number of pods the job should
run at any given time" and `completions` as "the desired number of
successfully finished pods the job should be run with". For
`completionMode`: "Indexed means that the Pods of a Job get an associated
completion index from 0 to (.spec.completions - 1), available in the
annotation batch.kubernetes.io/job-completion-index. The Job is considered
complete when there is one successfully completed Pod for each index. When
value is Indexed, .spec.completions must be specified and .spec.parallelism
must be less than or equal to 10^5." The pod name takes the form
`$(job-name)-$(index)-$(random-string)` and the hostname `$(job-name)-$(index)`.
`backoffLimit` "Defaults to 6, unless backoffLimitPerIndex (only Indexed
Job) is specified"; `backoffLimitPerIndex` counts retries within one index
and requires `completionMode: Indexed` and a `Never` restart policy;
`maxFailedIndexes` "must be less than or equal to 10^4 when is completions
greater than 10^5". `activeDeadlineSeconds` bounds how long a Job may be
continuously active, and "If a Job is suspended (at creation or through an
update), this timer will effectively be stopped and reset when the Job is
resumed again."

The [indexed parallel processing tutorial](https://kubernetes.io/docs/tasks/job/indexed-parallel-processing-static/)
adds that the control plane exposes the index in the
`JOB_COMPLETION_INDEX` environment variable, and its example
uses `completions: 5`, `parallelism: 3`, and `completionMode: Indexed`.

Suspension: the current concepts page's section "Suspending a Job" could
not be read because the fetch was truncated before it. The
[2021 blog post introducing suspended Jobs](https://kubernetes.io/blog/2021/04/12/introducing-suspended-jobs/)
describes the behavior: suspending a Job terminates its active pods (they
receive `SIGTERM` and their termination grace period), the Job status
records the suspension, resuming creates the pods again from the start, and
the feature was built for queueing systems that hold Jobs until resources
are available. The wording in this paragraph is a paraphrase because the
fetch did not return the sentences verbatim. The consequence for this
record is exact: a suspended Job is not a paused Job. In-memory state of
the pods is lost.

The Job in example 28 (`backoffLimit: 0`, `ttlSecondsAfterFinished:
86400`) matches the field semantics above: no silent retry, and finished
Jobs removed after one day.

### Adding capacity

The [Horizontal Pod Autoscaler page](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
states that it "automatically updates a workload resource (such as a
Deployment or StatefulSet), with the aim of automatically scaling capacity
to match demand", that it "does not apply to objects that can't be scaled
(for example: a DaemonSet)", and that the control loop interval "is set by
the --horizontal-pod-autoscaler-sync-period parameter to the
kube-controller-manager (and the default interval is 15 seconds)". The
algorithm is desiredReplicas = ceil[currentReplicas * (currentMetricValue /
desiredMetricValue)], with a tolerance of 0.1 and a scale-down
stabilization window of 300 seconds by default. Object and external
metrics (a queue length, for example) feed the same ratio.

The [node autoscaling page](https://kubernetes.io/docs/concepts/cluster-administration/cluster-autoscaling/)
states that when pods cannot be scheduled on the existing Kubernetes
nodes, new Kubernetes nodes can be added automatically, and that
consolidation removes a set of underutilized Kubernetes nodes.
Cluster Autoscaler and Karpenter are the two machine autoscalers that the
Kubernetes autoscaling special interest group sponsors. The page
also states that setting pod resource requests correctly matters as much
to the cluster's cost-effectiveness as optimizing machine utilization.

The [Cluster Autoscaler frequently asked questions](https://github.com/kubernetes/autoscaler/blob/master/cluster-autoscaler/FAQ.md)
(on github.com) state that it scales up when "there are pods that failed
to schedule on any of the current nodes due to insufficient resources", and
considers a Kubernetes node for removal when "The sum of cpu requests and
sum of memory requests of all pods running on this node are smaller than
50% of the node's allocatable" and the node has been unneeded for more than
10 minutes. Defaults: scan interval 10 seconds, maximum node provision time
15 minutes, scale-down unneeded time 10 minutes, utilization threshold 0.5.
The flags `--max-nodes-total`, `--cores-total` (a `min:max` range), and
`--memory-total` (a `min:max` range) cap the whole cluster. The page
states that the Cluster Autoscaler "should handle up to 1000 nodes running
30 pods each" (Kubernetes nodes).

The [Karpenter NodePool page](https://karpenter.sh/docs/concepts/nodepools/)
states: "The NodePool spec includes a limits section (spec.limits), which
constrains the maximum amount of resources that the NodePool can consume",
with `cpu: 1000` and `memory: 1000Gi` as example values; when a limit is
exceeded, provisioning stops until some Kubernetes nodes have been
terminated; and "Karpenter provisioning is highly parallel. Because of
this, limit checking is eventually consistent, which can result in overrun
during rapid scale outs." Consolidation (`WhenEmpty`,
`WhenEmptyOrUnderutilized`), `consolidateAfter`, `expireAfter`, and
disruption budgets (which control how fast Karpenter removes Kubernetes
nodes) are declared on the same object.

The [KEDA concepts page](https://keda.sh/docs/latest/concepts/) describes a
Kubernetes event driven autoscaler that scales "from zero to n based on
external event sources such as message queues, databases, or APIs" and
"works alongside Kubernetes' existing Horizontal Pod Autoscaler rather than
replacing it". The [scaling Jobs page](https://keda.sh/docs/latest/concepts/scaling-jobs/)
describes the `ScaledJob`: "For each detected event a single Kubernetes Job
is scheduled. That job will initialize, pull a single event from the message
source, and process to completion and terminate", with `pollingInterval`
defaulting to 30 seconds, `maxReplicaCount` to 100, and history limits of
100 successful and 100 failed Jobs; the page recommends it "to handle
processing long-running executions".

### Container checkpointing

The [kubelet checkpoint page](https://kubernetes.io/docs/reference/node/kubelet-checkpoint-api/)
is marked "Beta since Kubernetes v1.30; enabled by default". The endpoint
is `POST /checkpoint/{namespace}/{pod}/{container}`. "The kubelet will
specify the name of the checkpoint archive as
`checkpoint-<podFullName>-<containerName>-<timestamp>.tar` and also request
to store the checkpoint archive in the checkpoints directory below its root
directory", which "defaults to /var/lib/kubelet/checkpoints". The archive
is a tar file whose contents depend on the container runtime on that
Kubernetes node. The `timeout` query
parameter is in seconds and "Checkpoint creation time depends directly on
the used memory of the container. The more memory a container uses the more
time is required to create the corresponding checkpoint." The endpoint
answers 404 when the `ContainerCheckpoint` feature gate is disabled and 500
when the container runtime does not implement the checkpoint call.

The [feature gates reference](https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/)
lists `ContainerCheckpoint` as Alpha with default `false` from 1.25 to
1.29 and Beta with default `true` from 1.30. The enhancement is titled
forensic container checkpointing; the
[2022 blog post](https://kubernetes.io/blog/2022/12/05/forensic-container-checkpointing-alpha/)
states that it "is based on Checkpoint/Restore In Userspace (CRIU) and
allows the creation of stateful copies of a running container without the
container knowing that it is being checkpointed", that the Kubernetes
implementation "uses existing CRIU integration in CRI-O and CRIU", that a
checkpoint is restored by building a container image from the archive with
buildah and starting it with podman or in Kubernetes, and that restoring is
not part of the Kubernetes programming interface. Whether containerd
implements the checkpoint call on this date was not confirmed from the
pages read (unverified). The current kubelet page lists a checkpoint
endpoint and no restore endpoint.

### Stall handling: probes, termination, restarts, and eviction

The [probes page](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
describes liveness probes for a container that "has transitioned to a
broken state and cannot recover except by being restarted" (on failure
"the kubelet kills the container and restarts it" subject to the restart
policy), readiness probes for accepting traffic, and startup probes that
protect slow starting containers by delaying the other probes. The
mechanisms are `exec`, `httpGet` ("Any code greater than or equal to 200
and less than 400 indicates success"), `tcpSocket`, and `grpc`. Defaults:
`periodSeconds` 10, `timeoutSeconds` 1, `failureThreshold` 3, and a probe
may carry its own `terminationGracePeriodSeconds`.

The [pod lifecycle page](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
states: "The default terminationGracePeriodSeconds is 30 seconds", that
first `SIGTERM` is sent and after the grace period `SIGKILL`, and that
container restarts use an exponential back-off (10 seconds, 20 seconds, 40
seconds, capped at 300 seconds). Pod phases are `Pending`, `Running`,
`Succeeded`, `Failed`, and `Unknown`.

The [node-pressure eviction page](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)
describes node-pressure eviction (pressure on a Kubernetes node) as "the
process by which the kubelet proactively terminates pods to reclaim
resource" on the machine. The signals
include `memory.available`, `nodefs.available`, and `pid.available`; default
hard thresholds include `memory.available` below 100Mi and
`nodefs.available` below 10 percent; and "If you use hard eviction
thresholds, the kubelet uses a 0s grace period (immediate shutdown) for
termination." The [Quality of Service page](https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/)
states that when a Kubernetes node runs out of resources, Kubernetes evicts
`BestEffort` pods first, then `Burstable`, and `Guaranteed` pods last. A
solutioning node whose pod sets equal requests and
limits is `Guaranteed` and is evicted last.

The [resource management page](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
states: "cpu limits are enforced by CPU throttling", and "memory limits are
enforced by the kernel with out of memory (OOM) kills. When a container
uses more than its memory limit, the kernel may terminate it." Memory
limits are enforced reactively: "A container may use more memory than its
memory limit, but if it does, it may get killed."

The [in-place resize page](https://kubernetes.io/docs/tasks/configure-pod-container/resize-container-resources/)
is marked "Stable since Kubernetes v1.35" and lets the CPU and memory
requests and limits of a container change "without recreating the Pod".
The kubelet reports `PodResizePending` with reason `Infeasible` ("The
requested resize is impossible on the current node") or `Deferred` ("The
requested resize is currently not possible, but might become feasible
later"), and `PodResizeInProgress` while applying. The page has an example
titled "Resizing memory with restart"; the exact conditions under which a
memory decrease is refused without a restart were not captured
(unverified).

### What Kubernetes gives for each owner need

| Owner need | Kubernetes mechanism | Documented figure | Gap |
|---|---|---|---|
| Keep live solutioning nodes within capacity | Requests and limits per container, ResourceQuota per namespace, LimitRange defaults, 110 pods per Kubernetes node | 110, 5,000, 150,000, 300,000 (large cluster page) | None for counting; capacity is in CPU and memory, never in currency |
| Detect a stalled node | Liveness and startup probes, `activeDeadlineSeconds` on Jobs, restart back-off | period 10 seconds, timeout 1 second, 3 failures, back-off 10 to 300 seconds | A probe needs an endpoint or command inside the harness instance; a pod without one is only caught by the deadline |
| Clear a stalled node | Probe failure restarts the container; Job deadline terminates; grace period then `SIGKILL` | 30 seconds default grace | Restart loses the node's memory state |
| Pause a node under memory pressure | None for a running pod. Job suspend deletes pods. In-place resize can lower CPU and memory limits without recreating the pod | Stable since v1.35 | No freeze operation is exposed on the pod object (inferred: no page read describes one) |
| Hibernate and restore later | Kubelet checkpoint endpoint with CRIU through CRI-O; restore outside the Kubernetes programming interface | Beta since v1.30, enabled by default | No restore endpoint; containerd support unverified; archive size and time grow with memory |
| Spin up more capacity | Horizontal Pod Autoscaler, KEDA for queue-driven Jobs, Cluster Autoscaler or Karpenter for machines | 15 second loop; 10 second scan; provision time up to 15 minutes; NodePool `spec.limits` | Karpenter limit checks are eventually consistent and can overrun during rapid scale-out |

## 2. Batch and queueing on Kubernetes

### Kueue

The [Kueue concepts page](https://kueue.sigs.k8s.io/docs/concepts/) defines
a Workload as "An application that will run to completion. It is the unit
of admission in Kueue", a ClusterQueue as "A cluster-scoped resource that
governs a pool of resources, defining usage limits and Fair Sharing rules",
a LocalQueue as "A namespaced resource that groups closely related
workloads belonging to a single tenant", and a cohort as "a group of
ClusterQueues that can borrow unused quota from each other". Preemption is
"The process of evicting one or more admitted Workloads to accommodate
another Workload". Supported workloads include Kubernetes Jobs, CronJobs,
Deployments, StatefulSets, JobSets, Ray variants, and Kubeflow jobs.

The [ClusterQueue page](https://kueue.sigs.k8s.io/docs/concepts/cluster_queue/)
defines three quotas per resource: `nominalQuota` ("the quantity of this
resource that is available for a ClusterQueue at a specific time"),
`borrowingLimit` ("the maximum amount of quota that this ClusterQueue is
allowed to borrow from the unused nominal quota of other ClusterQueues"),
and `lendingLimit`. Queueing strategies are `StrictFIFO` ("Older workloads
that can't be admitted will block newer workloads") and `BestEffortFIFO`
(the default). Preemption is configured by `reclaimWithinCohort` (`Never`,
`LowerPriority`, `Any`), `withinClusterQueue` (`Never`, `LowerPriority`,
`LowerOrNewerEqualPriority`), and `borrowWithinCohort`. "StopPolicy allows
a cluster administrator to temporary stop the admission of workloads" with
`Hold` or `HoldAndDrain`. The [preemption page](https://kueue.sigs.k8s.io/docs/concepts/preemption/)
states that a preempted workload receives an `Evicted` condition with
reason `Preempted` and is requeued.

The [running Jobs page](https://kueue.sigs.k8s.io/docs/tasks/run/jobs/)
states: "you must set the kueue.x-k8s.io/queue-name label selecting the
LocalQueue you want to submit the Job to", "Kueue automatically manages the
Job's suspension via webhook and decides when it's the best time to start
the Job", "You should specify resource requests or limits for each Job
Pod", and that partial admission may start a Job with reduced parallelism
("The Job's completions count will not be changed"). The
[pending workloads page](https://kueue.sigs.k8s.io/docs/tasks/manage/monitor_pending_workloads/pending_workloads_on_demand/)
describes a visibility endpoint per ClusterQueue and per LocalQueue that
returns each pending workload with `positionInClusterQueue` and
`positionInLocalQueue`, behind role based access control on the
`clusterqueues/pendingworkloads` and `localqueues/pendingworkloads`
resources.

### Argo Workflows

The [architecture page](https://argo-workflows.readthedocs.io/en/latest/architecture/)
states that each step and each graph task causes a pod to be generated, with
three containers: an init container that fetches artifacts and parameters,
the main container running the user image, and a wait container that
"performs tasks that are needed for clean up, including saving off
parameters and artifacts". The [massive scale page](https://argo-workflows.readthedocs.io/en/latest/running-at-massive-scale/)
states: "It empowers you to process thousands of workflows per day, with
each workflow consisting of tens of thousands of nodes" (Argo's word
"nodes" means workflow steps) and advises pod and workflow garbage
collection, limiting concurrent workflows with parallelism, and
rate-limiting pod creation. The [scaling page](https://argo-workflows.readthedocs.io/en/latest/scaling/)
states: "You cannot horizontally scale the controller", the controller's
"memory usage is dominated by its informer caches, which hold every live
Workflow, Pod and related object it watches", the client rate limits
default to `--qps` 20 and `--burst` 30, and a pod creation rate limit is
configured as `limit: 10` and `burst: 25` in its example. The
[parallelism page](https://argo-workflows.readthedocs.io/en/latest/parallelism/)
documents a controller-level `parallelism` and a `namespaceParallelism`;
queued workflows start in priority order. The [field reference](https://argo-workflows.readthedocs.io/en/latest/fields/)
defines the workflow-level field as "Parallelism limits the max total
parallel pods that can execute at the same time in a workflow" and
`suspend` as "Suspend will suspend the workflow and prevent execution of
any future steps in the workflow". The [synchronization page](https://argo-workflows.readthedocs.io/en/latest/synchronization/)
adds semaphores from a ConfigMap and mutexes at workflow and template
level, and database-backed locks shared across controllers. The
[Argo Server page](https://argo-workflows.readthedocs.io/en/latest/argo-server/)
states that the Argo Server exposes a programming interface and a user
interface for workflows and that authentication is delegated to the Kubernetes control
plane server or an OAuth provider.

### Volcano

The [Volcano documentation](https://volcano.sh/en/docs/) describes "a cloud
native system for high-performance workloads, which has been accepted by
Cloud Native Computing Foundation (CNCF) as its first and only official
container batch scheduling project". It lists gang scheduling ("Ensure all
tasks of a job start simultaneously"), binpack scheduling, a multi-level
queue structure with resource inheritance, and "resource borrowing,
reclaiming and preemption between queues", with integrations for Spark,
TensorFlow, PyTorch, Flink, Argo, Ray, and others. The page was reachable;
its PodGroup object is referenced but not defined on the page read.

### What each gives for thousands of short solutioning nodes within a budget

| System | Unit it queues | Budget boundary | What it gives | What it does not give |
|---|---|---|---|---|
| Kueue | A Job (or another supported kind) as one Workload | `nominalQuota` per ClusterQueue, borrowing and lending limits within a cohort, a `PriorityClass` per Workload, `StopPolicy` to hold a tenant | Admission only when quota exists, preemption across tenants by policy, visibility of queue positions, no pods created until admitted | Nothing inside a pod: no stall detection, no pause of a running pod |
| Argo Workflows | A step, one pod each, inside a workflow graph | Controller and namespace parallelism, workflow-level parallelism, semaphores | A graph of steps with artifacts, retries, deadlines, suspend, and a server user interface | One controller that cannot scale horizontally; three containers per step; every step pays pod creation |
| Volcano | A PodGroup with gang scheduling | Hierarchical queues with borrowing, reclaim, and preemption | Batch scheduling for jobs that must start together | Not needed unless solutioning nodes must be co-scheduled as a group; its documentation read here does not define per-pod stall handling |
| KEDA ScaledJob | One Job per queue event | `maxReplicaCount` (100 by default) per ScaledJob | A queue length drives Job creation from zero | No cross-tenant quota; combine with ResourceQuota or Kueue |

## 3. Distributed task frameworks

These systems place many small tasks on shared, long-lived workers instead
of creating a pod per task. Each was read on 2026-09-18.

### Ray

The [tasks page](https://docs.ray.io/en/latest/ray-core/tasks.html) states:
"Ray enables arbitrary functions to be executed asynchronously on separate
worker processes." The [resources page](https://docs.ray.io/en/latest/ray-core/scheduling/resources.html)
states: "Ray resources are logical and don't need to have 1-to-1 mapping
with physical resources", "Resource requirements of tasks or actors do NOT
impose limits on actual physical resource usage", "By default, Ray tasks
use 1 logical CPU resource and Ray actors use 1 logical CPU for scheduling,
and 0 logical CPU for running", "The sum of the logical resource
requirements of all of the concurrently executing tasks and actors on a
given node cannot exceed the node's total logical resources" (a Ray node
is a machine), and the per-machine defaults are the machine's processors, "70% of 'available memory'" for the
logical memory resource, and "30% of 'available memory'" for the object
store. The [actors page](https://docs.ray.io/en/latest/ray-core/actors.html)
states: "An actor is essentially a stateful worker (or a service)." The
[actor fault tolerance page](https://docs.ray.io/en/latest/ray-core/fault_tolerance/actors.html)
states: "The default value of max_restarts is 0, meaning that the actor
won't be restarted", "When an actor is restarted, its state will be
recreated by rerunning its constructor", and `ray.kill` terminates an
actor. The [object spilling page](https://docs.ray.io/en/latest/ray-core/objects/object-spilling.html)
states: "Ray spills objects to a directory in the local filesystem once the
object store is full", by default under `/tmp/ray`.

The [out-of-memory prevention page](https://docs.ray.io/en/latest/ray-core/scheduling/ray-oom-prevention.html)
documents a memory monitor: `RAY_memory_usage_threshold` defaults to 0.95
("If the memory usage is above this fraction it will start killing
processes to free up memory"), `RAY_memory_monitor_refresh_ms` defaults to
250, "Amongst the tasks that share the same caller, the latest started task
will be killed first", "If tasks are killed by the memory monitor, it
retries infinitely (not respecting max_retries) unless max_retries is set
to 0", and "If actors are killed by the memory monitor, it doesn't recreate
the actor infinitely (It respects max_restarts, which is 0 by default)".

The [cluster key concepts page](https://docs.ray.io/en/latest/cluster/key-concepts.html)
states: "The autoscaler only reacts to task and actor resource requests,
and not application metrics or physical resource utilization." The
[KubeRay page](https://docs.ray.io/en/latest/cluster/kubernetes/index.html)
describes the `RayCluster`, `RayJob`, and `RayService` custom resources,
with "a head node pod and a collection of worker node pods". The
[KubeRay autoscaling page](https://docs.ray.io/en/latest/cluster/kubernetes/user-guides/configuring-autoscaling.html)
states that the autoscaler runs as "a sidecar container within the Ray head
Pod", that `minReplicas` and `maxReplicas` bound each worker group,
`idleTimeoutSeconds` defaults to 60 seconds, `upscalingMode` is
`Conservative`, `Default`, or `Aggressive`, and "if the Kubernetes cluster
lacks sufficient resources for the new Ray Pods that the Ray Autoscaler
creates, the Kubernetes Autoscaler can provision a new Kubernetes node. You
must configure the Kubernetes Autoscaler yourself." The
[dashboard page](https://docs.ray.io/en/latest/ray-observability/getting-started.html)
serves at port 8265 with Jobs, Cluster, Actors, Metrics, and Logs views;
"The Metrics view requires the Prometheus and Grafana setup."

No page read states a per-task latency or per-task memory figure for Ray
(missing). No page read describes a timeout that stops a task that hangs
while using no memory (missing).

### Dask

The [worker memory page](https://distributed.dask.org/en/stable/worker-memory.html)
documents four thresholds on the worker's memory limit: at 60 percent of
managed memory "the worker will begin to dump the least recently used data
to disk"; at 70 percent of process memory it spills regardless; "At 80%
process memory load, the worker's thread pool will stop starting
computation on additional tasks in the worker's queue"; and "At 95% process
memory load, a worker's nanny process will terminate it. Tasks will be
cancelled mid-execution and rescheduled elsewhere." The worker monitors
its process memory every 200 milliseconds. The
[worker page](https://distributed.dask.org/en/stable/worker.html)
describes the Nanny that "spins up Worker processes, watches them, and
kills or restarts them as necessary", the thread count that bounds tasks
per worker, a `lifetime` after which a worker shuts down, a
`heartbeat_interval` of 1 second, and a `worker-ttl` setting for
unresponsive workers. The [resources page](https://distributed.dask.org/en/stable/resources.html)
states that declared resources "are just abstract quantities" that Dask
does not enforce. The [adaptive page](https://docs.dask.org/en/stable/adaptive.html)
describes `cluster.adapt(minimum=0, maximum=100)`: the scheduler derives a
target worker count "by dividing the cumulative expected runtime of all
pending tasks by the target_duration parameter (defaults to five seconds)",
and "When scaling down, Dask preferentially chooses those workers that are
idle and have the least data in memory." The [dashboard page](https://docs.dask.org/en/stable/dashboard.html)
serves at `http://localhost:8787/status` and colors per-worker memory bars
for under target, near spill, paused or retiring, and spilled.

Dask's pause at 80 percent is the closest documented match to the owner's
"pause a node that is taking too much memory": the worker keeps its running
tasks and stops starting new ones. No page read states a per-task overhead
figure (missing).

### Celery with a broker

The [workers page](https://docs.celeryq.dev/en/stable/userguide/workers.html)
states: "The number of worker processes/threads can be changed using the
--concurrency argument and defaults to the number of CPUs available on the
machine"; the pools are prefork, eventlet, gevent, threads, and solo; "The
soft time limit allows the task to catch an exception to clean up before it
is killed: the hard timeout isn't catch-able and force terminates the
task"; autoscaling "needs two numbers: the maximum and minimum number of
pool processes" (`--autoscale=10,3`); two worker options replace a pool
process after it has executed a maximum number of tasks or reached a
maximum resident memory (their exact names are on the page and contain a
word that this repository's lint refuses); and remote control can inspect
active tasks and revoke a task with `terminate`. The
[tasks page](https://docs.celeryq.dev/en/stable/userguide/tasks.html)
defines per-task `time_limit` and `soft_time_limit`, warns that with
`acks_late` "the task may be executed multiple times should the worker
crash in the middle of execution", and warns that a task that allocates
too much memory risks the kernel's out-of-memory killer, and that the same
may happen again on retry. [Flower](https://flower.readthedocs.io/en/latest/) "is an
open-source web application for monitoring and managing Celery clusters."

Celery bounds concurrency per worker and detects a hung task by time limit
only. It has no pause. No page read states a per-task overhead figure
(missing).

### Temporal

The [workflows page](https://docs.temporal.io/workflows) states: "A
Workflow Execution is a running Workflow, which is created by combining a
Workflow Definition with a request to execute it." It describes workflows
that can run for years even if the underlying infrastructure fails (the
page's sentence contains punctuation this repository does not use, so it is
paraphrased), "If the application itself crashes, Temporal will
automatically recreate its pre-failure state so it can continue right where
it left off", and replay: "It starts the Workflow code from the beginning,
replays the Event History step by step, and uses that history to guide the
code back to the exact state as before." The
[activities page](https://docs.temporal.io/activities) states: "An Activity
is a normal function or method that executes a single, well-defined action
(either short or long running)" and "If an Activity attempt fails, it is
automatically retried using its Retry Policy." The
[activity failure detection page](https://docs.temporal.io/encyclopedia/detecting-activity-failures)
defines the Schedule-To-Start, Start-To-Close, Schedule-To-Close, and
Heartbeat timeouts; "We strongly recommend setting a Start-To-Close
Timeout" because "The Temporal Server doesn't detect failures when a Worker
loses communication with the Server or crashes. Therefore, the Temporal
Server relies on the Start-To-Close Timeout to force Activity retries"; and
"Each ping informs the Temporal Service that the Activity Execution is
making progress and the Worker has not crashed." The
[workers page](https://docs.temporal.io/workers) states: "A Worker Process
is responsible for polling a Task Queue, dequeueing a Task, executing your
code in response to a Task, and responding to the Temporal Service with the
results." The [worker tuning reference](https://docs.temporal.io/develop/worker-tuning-reference)
lists default concurrent slots per software development kit (Python: 100
workflow tasks, 100 activities, 100 local activities, 5 pollers each, a
workflow cache of 1,000; Go: 1,000 of each slot; Java: 200; TypeScript: 40
workflow tasks and 100 activities) and states that resource-based slot
suppliers "automatically adjust available Task slots based on CPU and
memory utilization"; the [runtime tuning page](https://docs.temporal.io/develop/worker-performance/runtime-tuning)
shows `targetMemoryUsage: 0.8, targetCpuUsage: 0.9` as an example. The
[activity command reference](https://docs.temporal.io/cli/activity) lists
`pause`, `unpause`, `reset`, and `update-options` (pause is marked
experimental): "if the Activity is currently running, it will run until the
next time it fails, completes, or times out, at which point the pause will
kick in", and "Pause does not stop or extend the Activity's
Schedule-To-Close Timeout. A paused Activity can still time out." The
[web interface page](https://docs.temporal.io/web-ui) states that
"Workflow Executions can request a Cancellation, send a Signal or Update,
or Reset and Terminate" directly from the web interface.

Temporal is the one system read here whose suspension model matches
hibernation without process images: a workflow's state is its event
history, so a worker can be stopped and the workflow continues on another
worker by replay. The in-flight activity attempt is lost and retried. No
page read states a per-activity overhead figure (missing).

### Comparison of the four frameworks

| Framework | Concurrency bound | Stalled work | Pause and resume | Per-task cost compared with a pod |
|---|---|---|---|---|
| Ray | Logical CPU and custom resources per worker process; not physically enforced | Memory monitor kills the newest task at 95 percent of the machine's memory, checked every 250 milliseconds; no hung-task timeout found on pages read | No pause; killed tasks retry, actors follow `max_restarts` | A reused worker process; no figure documented (missing) |
| Dask | Threads per worker; abstract resources not enforced | Heartbeats every 1 second and `worker-ttl`; the nanny terminates a worker at 95 percent memory | Pause at 80 percent memory (running tasks continue, no new tasks start); resume when memory drops | A thread in a reused worker; no figure documented (missing) |
| Celery | Pool size per worker (defaults to the processor count), autoscale range | Soft and hard time limits; revoke with terminate | No pause; pool processes replaced by task count or memory | A broker message and a pool process; no figure documented (missing) |
| Temporal | Slots per worker (Python defaults 100); resource-based slot suppliers by CPU and memory targets | Heartbeat timeout and Start-To-Close timeout; retries on another worker | Activity pause and unpause (experimental) affect retries, not the running attempt; workflows survive worker loss through replay | A persisted task and history events per activity; no figure documented (missing) |

Inferred for all four: a task on a reused worker costs a dispatch and the
transfer of its inputs, with no process start and no scheduling by the
Kubernetes control plane. A pod per task adds container creation, the
documented start latency of up to 5 seconds at the 99th percentile before
image pulls, per-pod bookkeeping in the control plane, and the image
itself. None of the four frameworks measures memory per task; each bounds
memory at the worker.

## 4. Sandboxing shapes for untrusted work

| Shape | What isolates | Startup | Memory overhead | Pause and snapshot | Source |
|---|---|---|---|---|---|
| Plain container (runc through containerd or CRI-O) | Linux namespaces and control groups on the shared host kernel | No figure on the pages read; the Kubernetes pod service level objective is 5 seconds at the 99th percentile; a bare Python process started in 11 milliseconds on this machine | The process itself; 9 MiB resident for a bare Python interpreter on this machine | `docker pause` through the freezer cgroup; `podman container checkpoint` with CRIU | Sections 1 and 5 |
| gVisor | An application kernel in user space (the Sentry) intercepting system calls; the Gofer for files; `runsc` as the container runtime; `systrap` is the default platform since mid-2023, and the kernel virtual machine (KVM) platform "runs best on bare-metal setups" | No figure on the pages read (missing) | No figure on the pages read (missing); the performance page says the Sentry "requires memory in order to store state associated with the application" | Not described on the pages read | [gVisor documentation](https://gvisor.dev/docs/), [platforms](https://gvisor.dev/docs/architecture_guide/platforms/), [performance](https://gvisor.dev/docs/architecture_guide/performance/) |
| Kata Containers | "lightweight virtual machines" that "feel and perform like standard Linux containers, but provide stronger workload isolation using hardware virtualization technology as a second layer of defence"; a shim v2 runtime, the kata-agent inside the guest, and QEMU, Cloud Hypervisor, or Firecracker as hypervisor | No figure on the page read (missing) | The Kubernetes pod overhead example for `kata-fc` is 120Mi and 250m per pod (an example, not a measurement) | Not described on the page read | [Kata architecture](https://github.com/kata-containers/kata-containers/blob/main/docs/design/architecture/README.md) |
| Firecracker | A minimal virtual machine monitor over the KVM interface; each guest is a small virtual machine that Firecracker calls a microVM | 125 milliseconds or less from the start request to the start of the guest's `/sbin/init` process; the monitor starts within 8 processor-milliseconds | "Firecracker's virtual machine manager threads have a memory overhead <= 5 MiB" (guest memory is additional); compute performance "> 95% of the equivalent bare-metal performance"; specified on a microVM with 1 processor and 128 MiB | Snapshots exist in Firecracker but were not read for this record | [Firecracker specification](https://github.com/firecracker-microvm/firecracker/blob/main/SPECIFICATION.md) |
| E2B (agent sandboxes) | "Every session receives a hardware-isolated Firecracker microVM rather than a shared-kernel container" | A startup time is not stated on the pages read (missing); the lifecycle page returned 404 | Not stated (missing) | "Pausing a sandbox saves both its filesystem and its memory"; pausing takes about 4 seconds per GiB of memory (the page's figure); "Resuming a sandbox takes approximately 1 second"; "A paused sandbox is kept indefinitely"; the site states it can "fork up to 100 copies from a saved state" | [E2B documentation](https://docs.e2b.dev/), [persistence](https://docs.e2b.dev/sandbox/persistence), [site](https://e2b.dev/) |
| Modal Sandboxes | "Compute jobs at Modal are containerized and virtualized using gVisor" | Not stated (missing) | Not stated (missing) | "Sandboxes have a default maximum lifetime of 5 minutes", extendable to 24 hours; an `idle_timeout`; filesystem snapshots become images (kept 30 days by default); memory snapshots are "copies of a Sandbox's entire state, both in memory and on the filesystem", experimental, and "expire 7 days after creation" | [Modal sandbox guide](https://modal.com/docs/guide/sandbox), [snapshots](https://modal.com/docs/guide/sandbox-snapshots), [security](https://modal.com/docs/guide/security) |

Inferred ordering of cost: a plain container adds the least (a process
plus namespaces), gVisor adds a user-space kernel per sandbox with no
figure published on the pages read, and a virtual machine runtime adds a
guest kernel and its memory (the Kubernetes example budgets 120Mi and 250m
per pod for Kata with Firecracker, and Firecracker itself specifies 5 MiB
or less for its monitor threads, with the guest's own memory on top). The
owner asked for startup times: the only documented ones read here are
Firecracker's 125 milliseconds or less to the guest's init process and
E2B's roughly 1 second resume from a paused state.

## 5. Local resource detection and control on Linux

All kernel, systemd, manual page, CRIU, Podman, Docker, Python, and psutil
pages in this section were read on 2026-09-18.

### Detection

The [proc_meminfo manual page](https://man7.org/linux/man-pages/man5/proc_meminfo.5.html)
defines `MemTotal` as the total usable physical memory (minus a few
reserved bits and the kernel binary code) and `MemAvailable` (since Linux
3.14) as "An estimate of how much memory is available for starting new
applications, without swapping", and `Committed_AS` as "The amount of
memory presently allocated on the system". `MemAvailable` is the figure a
supervisor should read for admission; `MemFree` excludes reclaimable cache
and understates what a new process can get.

The [pressure stall information (PSI) page](https://docs.kernel.org/accounting/psi.html)
states that the feature "identifies and quantifies the disruptions caused
by such resource crunches" and exposes `/proc/pressure/cpu`,
`/proc/pressure/memory`, and `/proc/pressure/io`, each with two lines of
the form `some avg10=0.00 avg60=0.00 avg300=0.00 total=0` and `full ...`.
"The 'some' line indicates the share of time in which at least some tasks
are stalled on a given resource", and "The 'full' line indicates the share
of time in which all non-idle tasks are stalled on a given resource
simultaneously"; the averages cover ten, sixty, and three hundred second
windows and `total` is absolute stall time in microseconds. Control groups
expose `cpu.pressure`, `memory.pressure`, and `io.pressure` in the same
format, and a process can register a trigger by writing
`<some|full> <stall amount in us> <time window in us>` to a pressure file
and waiting with `poll()`. A trigger is how a supervisor can be woken by
memory pressure instead of polling on an interval.

The [control group version 2 page](https://docs.kernel.org/admin-guide/cgroup-v2.html)
defines `memory.current` ("The total amount of memory currently being used
by the cgroup and its descendants"), `memory.peak` ("The max memory usage
recorded for the cgroup and its descendants since either the creation of
the cgroup or the most recent reset"), `memory.events` with `oom` and
`oom_kill` counts, `memory.events.local` for non-hierarchical counts,
`memory.stat` with `anon` and `file`, `cpu.stat` with throttling fields,
`cgroup.procs` (the process identifiers in the group), and `cgroup.events`
with `populated` and `frozen` keys.

### Control

The same control group page defines `memory.max` ("Memory usage hard
limit. This is the main mechanism to limit memory usage of a cgroup"; when
usage reaches the limit and cannot be reduced, the kernel's out-of-memory
killer runs inside the group), `memory.high` ("Memory usage throttle
limit. If a cgroup's usage goes over the high boundary, the processes of
the cgroup are throttled and put under heavy reclaim pressure"),
`memory.min` and `memory.low` (protection from reclaim), `memory.swap.max`,
`memory.oom.group` ("If set, all tasks belonging to the cgroup or to its
descendants are killed together or not at all"), `cpu.max` (the format
`$MAX $PERIOD`, default `max 100000`), `cpu.weight` (default 100, range 1
to 10000), `pids.max` ("Hard limit of number of processes"), `cgroup.freeze`
("Writing '1' to the file causes freezing of the cgroup and all descendant
cgroups. This means that all belonging processes will be stopped and will
not run until the cgroup will be explicitly unfrozen"), and `cgroup.kill`
("Writing '1' to the file causes the cgroup and all descendant cgroups to
be killed. This means that all processes located in the affected cgroup
tree will be killed via SIGKILL").

The [systemd-run manual page](https://man7.org/linux/man-pages/man1/systemd-run.1.html)
states: "systemd-run may be used to create and start a transient .service
or .scope unit and run the specified COMMAND in it." With `--scope`, "it
will be executed by systemd-run itself as parent process and will thus
inherit the execution environment of the caller"; `--property` "Sets a
property on the scope or service unit that is created"; `--user` talks "to
the service manager of the calling user, rather than the service manager
of the system"; and `--unit` names the unit. The
[resource control manual page](https://man7.org/linux/man-pages/man5/systemd.resource-control.5.html)
maps `MemoryMax=` to `memory.max` ("If memory usage cannot be contained
under the limit, out-of-memory killer is invoked inside the unit"),
`MemoryHigh=` to `memory.high`, `MemorySwapMax=` to `memory.swap.max`,
`CPUQuota=` to `cpu.max`, `CPUWeight=` to `cpu.weight`, and `TasksMax=` to
`pids.max`. A transient scope is therefore the way an unprivileged
supervisor gets a control group per harness instance that captures the
whole process tree, including the shells, tests, and builds that a coding
harness spawns.

The [signal manual page](https://man7.org/linux/man-pages/man7/signal.7.html)
lists `SIGSTOP` ("Stop process"), `SIGCONT` ("Continue if stopped"),
`SIGTERM`, and `SIGKILL`, and states: "The signals SIGKILL and SIGSTOP
cannot be caught, blocked, or ignored." The
[docker pause reference](https://docs.docker.com/reference/cli/docker/container/pause/)
contrasts the two pause mechanisms: "On Linux, this uses the freezer
cgroup. Traditionally, when suspending a process the SIGSTOP signal is
used, which is observable by the process being suspended. With the freezer
cgroup the process is unaware, and unable to capture, that it is being
suspended, and subsequently resumed." `SIGSTOP` acts on one process
identifier (a process group needs `killpg`); the freezer acts on a whole
control group.

### Hibernation with CRIU

The [CRIU main page](https://criu.org/Main_Page) states: "It can freeze a
running container (or an individual application) and checkpoint its state
to disk. The data saved can be used to restore the application and run it
exactly as it was during the time of the freeze." It lists integrations
into OpenVZ, LXC, LXD, Incus, Docker, Podman, and Kubernetes, and a
release 4.2.1 dated 21 July 2026. The page listing what can be
checkpointed returned 404; the [page listing what cannot](https://criu.org/What_cannot_be_checkpointed)
was read and states: for devices, "If a task has opened or mapped any
character or block device, this typically means, it wants some connection
to the hardware. In this case dump (and restore) is impossible" (virtual
devices such as null, zero, and TUN are exceptions, so a process holding a
graphics device cannot be dumped); open files from lazily unmounted
filesystems; tasks under a debugger ("tasks under gdb or strace cannot be
dumped"); other users' tasks when CRIU runs unprivileged; socket types
other than TCP, UDP, UNIX, packet, and netlink; and applications connected
to a real X server. The [TCP connection page](https://criu.org/TCP_connection)
states that established connections need the `TCP_REPAIR` socket option
(kernel 3.5 and later), that while the socket is closed between dump and
restore the connection must be locked so that no packet from the peer
enters the stack (otherwise the kernel would send a reset), that the
caller must pass `--tcp-established`, and that the network address the
connection used must be available again on restore.

The [podman container checkpoint page](https://docs.podman.io/en/latest/markdown/podman-container-checkpoint.1.html)
"Checkpoints all the processes in one or more containers" with `--export`
to an archive, `--leave-running`, `--tcp-established` ("If the checkpoint
image contains established TCP connections, this OPTION is required during
restore"), `--pre-checkpoint` ("Dump the container's memory information
only, leaving the container running") for a lower-downtime final dump,
`--file-locks`, and the caveat "If the container is using systemd as
entrypoint checkpointing the container might not be possible."

Inferred consequence for a harness instance: a solutioning node that holds
an open connection to a model provider, that has a debugger or tracer
attached, or that holds a graphics device cannot be dumped as a process
image without first closing or locking those resources. An
application-level checkpoint (the Loop's own records, working folder, and
the harness's own session state) does not have those limits but loses
whatever the harness keeps only in memory.

### Python standard library and psutil

The [resource module](https://docs.python.org/3/library/resource.html)
provides `getrlimit`, `setrlimit`, and `prlimit` (Linux, for another
process, needing `CAP_SYS_RESOURCE`), with `RLIMIT_AS` ("The maximum area
(in bytes) of address space which may be taken by the process"),
`RLIMIT_CPU` ("The maximum amount of processor time (in seconds) that a
process can use. If this limit is exceeded, a SIGXCPU signal is sent to the
process"), `RLIMIT_NPROC`, `RLIMIT_DATA`, and `RLIMIT_RSS` ("The maximum
resident set size that should be made available to the process"), and
`getrusage`. The [signal module](https://docs.python.org/3/library/signal.html)
defines `signal.SIGSTOP` ("Stop executing (cannot be caught or ignored)"),
`signal.SIGCONT` ("Continue the process if it is currently stopped"),
`signal.SIGTERM`, `signal.SIGKILL`, and `signal.SIGXCPU` ("CPU time limit
exceeded"), and states: "Python signal handlers are always executed in the
main Python thread of the main interpreter". The
[subprocess module](https://docs.python.org/3/library/subprocess.html)
provides `Popen.send_signal`, `Popen.terminate` (sends `SIGTERM` on POSIX
systems), `Popen.kill` (sends `SIGKILL`), `Popen.poll`,
`Popen.wait(timeout)` (raises `TimeoutExpired`), a `timeout` on
`subprocess.run` after which the subprocess is killed and waited for,
`start_new_session` ("the setsid()
system call will be made"), and `process_group` (`setpgid`). Starting a
harness instance in its own session or process group is what makes
`os.killpg` reach the whole tree.

The [os module page](https://docs.python.org/3/library/os.html) was
fetched but truncated before the process functions, so the following are
observed from the docstrings of Python 3.14.4 on this machine rather than
from the web page: `os.cpu_count` ("Return the number of logical CPUs in
the system"), `os.process_cpu_count` ("Return the number of logical CPUs
usable by the calling thread"), `os.sched_getaffinity`, `os.getloadavg`
("Return the number of processes in the system run queue averaged over"
one, five, and fifteen minutes), `os.kill`, `os.killpg`, and `os.waitpid`.

The [psutil documentation](https://psutil.readthedocs.io/en/stable/)
defines `psutil.virtual_memory()` with `total` ("total physical memory
(exclusive swap)"), `available` ("the memory that can be given instantly to
processes without the system going into swap"), and `percent` ("(total -
available) / total * 100"), and advises: "if you just want to know how much
physical memory is left in a cross platform fashion simply rely on
available and percent fields"; `psutil.cpu_percent(interval)`;
`psutil.getloadavg()`; `Process.memory_info()` with `rss` ("the non-swapped
physical memory a process has used") and `vms`; `Process.memory_full_info()`
with `uss` ("the memory which is unique to a process and which would be
freed if the process was terminated right now"), `pss`, and `swap`;
`Process.suspend()` and `Process.resume()` (their docstrings in psutil
7.1.0 on this machine read "Suspend process execution with SIGSTOP" and
"Resume process execution with SIGCONT", each after checking that the
process identifier has not been reused); `Process.terminate()`
(`SIGTERM`); `Process.kill()` (`SIGKILL`); the method that lists a process's
descendants (with a recursive option); `psutil.wait_procs()` ("Return a
(gone, alive) tuple"); `Process.status()`; `Process.rlimit()`; and
`Process.oneshot()`. The `uss` figure is the one to sum when deciding how
much memory pausing or stopping an instance would actually free; `rss`
double counts shared pages.

### What this machine showed on 2026-09-18

Observed on the development machine (Linux 7.0.0-31-generic, Python
3.14.4, psutil 7.1.0). These are measurements, not limits.

| Measurement | Value |
|---|---|
| Processors (`os.cpu_count`, `os.process_cpu_count`, affinity) | 16, 16, 16 |
| Memory (`/proc/meminfo`) | `MemTotal` 64,550,844 kB; `MemAvailable` 18,601,492 kB at the time of reading; psutil reported 71.2 percent used |
| Load average (one minute) | 4.2 |
| `/proc/pressure/memory` | `some avg10=0.00 avg60=0.00 avg300=0.00` (no memory stall) |
| `/proc/pressure/cpu` | `some avg10=0.45 avg60=0.78 avg300=0.97`, `full` 0.00 |
| Control groups | version 2 mounted at `/sys/fs/cgroup` with the controllers `cpuset cpu io memory hugetlb pids rdma misc dmem`; the shell ran under `user.slice/user-1000.slice/user@1000.service/app.slice/` |
| Transient user scope | `systemd-run --user --scope -p MemoryMax=200M -p MemoryHigh=150M -p CPUQuota=50% -p TasksMax=64` produced a scope whose files read `memory.max` 209715200, `memory.high` 157286400, `cpu.max` `50000 100000`, `pids.max` 64, and `cgroup.freeze` 0, with its own `memory.pressure` and `memory.current` (3,907,584 bytes for the probe) |
| Freeze, thaw, kill | `systemctl --user freeze` on the scope set `cgroup.events` to `frozen 1`; `systemctl --user thaw` returned it to `frozen 0`; writing 1 to `cgroup.kill` ended every process in the scope and the scope disappeared |
| A bare Python process | 11 milliseconds to print a line; 9 MiB resident, 3 MiB unique |
| `import loop_engine` | 10 milliseconds; 10 MiB resident, 3 MiB unique |
| `import loop_engine.solve_cli` | 46 milliseconds; 17 MiB resident, 10 MiB unique |
| `import loop_engine.adaptive_practitioner_cli` | 22 milliseconds; 12 MiB resident, 5 MiB unique |
| Sandboxing tools | `docker` present; `criu`, `runsc`, `kata-runtime`, `firecracker`, and `kubectl` absent |

Inferred: an unprivileged user on this machine can already give each
harness instance a control group with a memory throttle, a memory ceiling,
a processor quota, and a process count ceiling, can freeze and thaw it
without the process observing a signal, and can end the whole tree with
one write. The in-process Practitioner costs on the order of 10 to 17 MiB
before it does any work. The memory of an external coding harness process
was not measured (assumed: on the order of one hundred to several hundred
MiB resident for a process built on a JavaScript runtime; the local
supervisor samples memory per instance, so a first campaign can replace
this assumption with measurements).

## 6. Cost and budget control in the cloud

No page read describes a Kubernetes object that holds a currency amount
(inferred from the pages in section 1; stated as an absence, not as a
verified fact about every Kubernetes distribution). A client's budget in
money therefore has to be converted into capacity units by the operator and
then expressed through the objects below.

```text
Client budget in currency
└── converted by the operator into capacity (owner sets the rate)
    ├── Namespace per tenant
    │   ├── ResourceQuota: requests.cpu, requests.memory, pods, count/jobs.batch
    │   └── LimitRange: default and maximum per container, request-to-limit ratio
    ├── Queue per tenant (Kueue)
    │   ├── ClusterQueue nominalQuota with borrowingLimit and lendingLimit
    │   ├── PriorityClass with a quota scope, so high priority is itself rationed
    │   └── StopPolicy Hold or HoldAndDrain when the budget is spent
    ├── Machines for the whole cluster
    │   ├── Cluster Autoscaler: --max-nodes-total, --cores-total, --memory-total
    │   └── Karpenter NodePool spec.limits (eventually consistent; can overrun)
    ├── Waste control per Job
    │   ├── activeDeadlineSeconds and backoffLimit
    │   └── ttlSecondsAfterFinished
    └── Allocation of the bill back to tenants
        └── OpenCost over namespaces, using the provider's billing data
```

The [OpenCost documentation](https://www.opencost.io/docs/) states:
"OpenCost is a vendor-neutral open source project for measuring and
allocating cloud infrastructure and container costs", "built for
Kubernetes cost monitoring to power real-time cost monitoring, showback,
and chargeback", with a specification that "describes a vendor-neutral
implementation for Kubernetes cost monitoring" and an integration for
"Cloud Costs from your provider's bill". The page read does not spell out
the allocation keys (namespace, label, pod); those were not verified.

The [pod priority page](https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/)
states: "If a Pod cannot be scheduled, the scheduler tries to preempt
(evict) lower priority Pods to make scheduling of the pending Pod possible"
and warns: "In a cluster where not all users are trusted, a malicious user
could create Pods at the highest possible priorities, causing other Pods to
be evicted/not get scheduled. An administrator can use ResourceQuota to
prevent users from creating pods at high priorities." `preemptionPolicy:
Never` gives a class that waits in queue order without evicting others.

Loop Engine already keeps model-call authority and metering separate from
compute: per-run call authority is declared, and the hosted service meters
verified completions, avoided model calls, optimize hours, and judgment
depth. Compute capacity is a new dimension next to those, not a
replacement for them.

What the owner must decide before any of this is built:

1. The conversion rate from currency to capacity (CPU-hours, memory
   GiB-hours, or a fixed reservation), and whether it is per tenant or
   global.
2. Whether a tenant may borrow beyond its nominal quota when the cluster is
   idle (Kueue cohorts) and who pays for the borrowed share.
3. Whether the cluster-wide machine limit is a hard cap (Cluster
   Autoscaler totals) or a soft one that Karpenter may overrun briefly.
4. The priority order between tenants and between solutioning work,
   verification work, and exported-solution Jobs.
5. Whether model-call spend and compute spend share one budget or two.
6. Retention of finished Jobs and checkpoint archives, which cost storage.
7. Who approves an overrun, and whether a spent budget holds the queue
   (`Hold`) or also drains running work (`HoldAndDrain`).

## 7. Recommendation and decision table

This section proposes shapes and states their overhead. It does not decide.
Every figure is labeled: documented (from a page read), measured (on this
machine), or estimate (this record's arithmetic or assumption).

| Shape | Unit of one solutioning node | Concurrency bound | Stall detection | Pause | Hibernate | Per-node overhead | Open questions |
|---|---|---|---|---|---|---|---|
| A. Local runs on one machine | A process in a transient systemd user scope with `MemoryHigh`, `MemoryMax`, `CPUQuota`, and `TasksMax` (measured working here); `RLIMIT_AS` as a weaker fallback where systemd is absent | The existing supervisor's ceiling (processor count unless declared) and memory reserve, plus a pressure stall information trigger for wake-up instead of polling | Heartbeat age (the existing 300 second default), plus processor time that stops growing (`getrusage`) and a per-node deadline | `SIGSTOP` on the process (existing controller) or `cgroup.freeze` on the scope, which the process cannot observe and which covers the whole tree | CRIU through `podman container checkpoint` only when nodes run as containers, `criu` is installed, and open provider connections are closed or locked; otherwise an application-level checkpoint from the Loop's records and working folder | Measured: 10 to 17 MiB and 10 to 46 milliseconds for the in-process Practitioner; estimate: one hundred to several hundred MiB for an external harness process | Whether the harnesses' own session persistence can serve as their part of an application-level checkpoint; how the supervisor learns each harness's process identifier and scope |
| B. One cluster, one pod per solutioning node | A Job with one pod (as example 28's Job), with a `RuntimeClass` when the work is untrusted | ResourceQuota `pods` and `requests.*` per namespace; Kueue `nominalQuota`; 110 pods per Kubernetes node (documented) | Liveness and startup probes (documented defaults), `activeDeadlineSeconds`; the Job's own deadline is the only catch for a pod without a probe | None native: Job suspend deletes the pods; in-place resize can lower limits (stable since v1.35) | Kubelet checkpoint endpoint (beta since v1.30) with CRIU through CRI-O and a restore outside the Kubernetes programming interface; or a sandbox provider's pause (E2B: about 4 seconds per GiB to pause, about 1 second to resume) | Documented: up to 5 seconds start at the 99th percentile before image pull; 120Mi and 250m per pod with Kata and Firecracker (example value); Firecracker monitor 5 MiB or less plus guest memory; estimate: a few MiB of pod bookkeeping and an image pull on a fresh machine | Where the task working folder lives when the pod dies (`emptyDir` is lost); how many pods per second the control plane accepts (Argo's client defaults of 20 requests per second and 30 burst are a reference, not a Kubernetes limit) |
| C. One cluster, a worker pool hosting many solutioning nodes per pod | A process inside a long-lived worker pod; the pod's memory limit bounds the sum | Slots per worker (the framework pattern: Ray logical resources, Dask threads, Celery pool size, Temporal slots) plus the supervisor's ceiling inside the pod; the Horizontal Pod Autoscaler or KEDA scales worker pods by queue depth; Cluster Autoscaler or Karpenter adds machines | In-pool heartbeats (the existing supervisor) plus a framework timeout (Celery time limits, Temporal heartbeat and Start-To-Close timeouts) | `SIGSTOP` inside the pod works today; `cgroup.freeze` per solutioning node needs a writable control group subtree inside the container, which was not verified | CRIU inside a container needs privileges that were not verified; prefer the application-level checkpoint | Measured: a process (10 to 17 MiB for the in-process Practitioner) rather than a pod; no scheduling latency beyond dispatch; estimate: the pod itself is paid once per worker | A memory spike in one solutioning node can push the whole pod over `memory.max`, and the kernel kills one process in the group (or all, with `memory.oom.group`); Dask's pause at 80 percent and Ray's monitor at 95 percent are the reference patterns to copy inside the pool |
| D. Thousands of solutioning nodes | A queue with quotas (Kueue ClusterQueue per tenant with cohorts and preemption, or KEDA ScaledJob) feeding a worker pool per tenant (shape C), with a Job per exported solution (shape B) and Indexed Jobs for batches | Kueue quotas and `StopPolicy`; documented ceilings 150,000 pods per cluster, 110 per Kubernetes node, 5,000 Kubernetes nodes; Indexed Job parallelism up to 10^5 | Temporal-style heartbeat and Start-To-Close timeouts inside the pool; probes per pod for exported solutions | Kueue `Hold` or `HoldAndDrain` per queue; Job suspend (deletes pods); in-pool pause | Application-level checkpoint; a sandbox provider's pause where sandboxes are external | Inferred: 3,000 simultaneous pods need at least 28 machines; a pool of 3,000 processes at 17 MiB each needs about 51 GiB before their work, so memory per solutioning node dominates the count, not the processor count | Whether one controller can hold the informer caches for that many pods (Argo documents that its controller cannot scale horizontally and is memory bound by its caches); which system owns the queue position that a client administrator sees |

### Measured on this machine on 2026-09-18

Ten runs of each, wall clock from the command starting to the command
exiting, on the development host with the published worker image already
pulled, so no image pull is included.

| What starts | Runs | Median | Lowest | Highest |
|---|---|---|---|---|
| One container from the published worker image, interpreter starting and exiting | 10 | 230.4 milliseconds | 222.6 | 250.1 |
| One process, interpreter starting and exiting | 10 | 10.4 milliseconds | 9.8 | 11.2 |
| One process that also imports the engine package root | 10 | 10.6 milliseconds | 10.2 | 11.2 |

Every run exited zero. On this machine a container start costs about
twenty-two times a process start. The third row imports the package root
only, which is a light import; it is not the cost of loading a Practitioner
with its intelligence.

What this measurement decides and what it does not. It supports the choice
between shape B and shape C when nodes are short: a node whose useful work
is under a second pays more than a fifth of a second for its own container,
while a process in a pool pays about a hundredth. It says nothing about
scheduling latency in a cluster, image pull on a cold machine, or the
memory a container holds, and it was taken on one machine with one image.

Which figures are documented limits: 110 pods per Kubernetes node, 5,000
Kubernetes nodes, 150,000 pods, and 300,000 containers; the 5 second pod
startup service level objective at the 99th percentile; the Kata with
Firecracker example overhead of 120Mi and 250m; Firecracker's 125
milliseconds or less boot and 5 MiB or less monitor overhead; E2B's 4
seconds per GiB pause and 1 second resume; Indexed Job parallelism of at
most 10^5; the probe, grace period, back-off, and eviction defaults; the
Dask and Ray memory thresholds; the Temporal slot defaults. Which figures
are measurements on this machine: the process start times and memory
figures, the scope test, and the container against process start comparison
in the section above. Which figures are estimates: the memory of an
external harness process, the pod bookkeeping cost, the pod creation rate,
and the arithmetic for 3,000 nodes.

Assumed for every shape, pending owner direction: the supervisor is an
internal runtime mechanic used by a classified Loop (the Starting Loop of a
campaign, or a Practitioner profile that owns placement), consistent with
the repository rule that capabilities and internal mechanics are not graph
vertices and that the work using them is owned by a Loop. No new runtime
type is implied by any shape above.

Open questions that no page read answers:

1. Whether containerd (the runtime in most managed clusters) implements
   the checkpoint call on this date, and whether a checkpoint can be
   restored in place by the kubelet rather than through an image build.
2. Whether a worker pod can create control group subtrees for its
   solutioning nodes without extra privileges, which decides whether
   per-node `memory.high` and `cgroup.freeze` are available in shape C.
3. The real memory and start time of each external harness (OpenCode,
   Codex, Pi) as a solutioning node, which decides the pool size.
4. Whether the harnesses' own session persistence is enough for an
   application-level hibernate, or whether the Loop must also save the
   harness's working state.
5. The pod creation rate the target cluster's control plane sustains,
   which decides whether shape B alone can reach thousands of short nodes
   per hour.

## 8. What administrators need to see and do

| Need | System administrator | Client administrator | What Loop Engine has on this date | Missing |
|---|---|---|---|---|
| Resource state per machine and per worker | All machines and pools: `MemAvailable`, pressure stall information, control group usage, pod counts; in a cluster, the resource metrics pipeline (CPU and memory usage for the machines and pods, read with `kubectl top`) | Their own namespace's usage against quota | `resource_snapshot/v1` from the local supervisor committed in `e4b543b` (one machine, in memory); `runtime_capacity` measurements | A persisted store for snapshots across machines; a view in Studio (it shows no resource state today) |
| Budgets and spend | Cluster totals, autoscaler limits, per-tenant quotas, the bill allocated by OpenCost | Their budget, its capacity conversion, remaining quota, and the metered units | `tenant_usage/v1` totals from the `usage` endpoint (verified completions, avoided model calls, optimize hours, judgment depth); tenant records with namespaces | A budget object with a currency conversion, alerts, and a hard stop; ResourceQuota and Kueue objects generated from it; a client-facing write surface (the service has no quota endpoint) |
| Solutioning node counts and states | Live, paused, hibernated, stalled, and stopped instances across every machine and pool, with the owning Loop and tenant | The same for their own runs | `instance_ledger/v1` with states and an event log (one machine, in memory); Studio's per-run spawned tasks and external harness summaries | A cross-machine inventory; the mapping from a solutioning node to its pod or Job identity; the `hibernated` state has no mechanism |
| Stalled nodes and the actions pause, resume, stop, hibernate | Act on any instance, with the reason recorded | Act on their own instances within their authority | `supervision_report/v1` records every automatic action with its reason; `SignalController` acts on owned process identifiers only; Studio accepts GET requests only | An authorized write surface where each action is an approval bound to the exact effect (the repository rule for effects); role separation between the two administrators; Kueue's `StopPolicy` and pending-workload positions as the cluster-side equivalents |
| Logs and playback | Machine and pod logs, supervisor event logs, the cluster's log pipeline | Their runs' Run History and playback | Run History, Studio playback with its privacy boundary (no prompts, tool arguments, or artifact bodies) | Supervisor events joined to Run History so a pause or stop appears on the run's timeline; `loop.paused` and `loop.resumed` exist in the vocabulary, and this record did not verify what emits them |
| Capacity growth | Approve autoscaler limits and machine classes | Request more capacity within budget | Nothing | The spin-up policy of roadmap step S-4.8 |

Reference front ends that the systems in sections 2 and 3 ship, read on
2026-09-18: the Ray Dashboard on port 8265 (cluster, actors, jobs, metrics
with Prometheus and Grafana), the Dask dashboard on port 8787 (per-worker
memory with paused and spilled states, task stream), Flower for Celery,
the Temporal web interface (list executions, event history, workers per
task queue, pending activities, and the actions cancel, signal, update,
reset, and terminate), the Argo Server user interface, the Kueue visibility
endpoints (pending workloads with queue positions behind role based access
control), and `kubectl top` over the metrics pipeline. None of them knows a
Loop, a tenant budget in currency, or Loop Engine's metering units; each
shows the pattern of what a resource front end presents: current usage
against a limit, a list of units of work with states, and a small set of
actions with a recorded reason.

## Facts that stayed unverified

- The "Suspending a Job" section of the current Kubernetes Job concepts
  page (the fetch was truncated); the semantics are taken from the 2021
  blog post and paraphrased.
- Whether containerd implements the checkpoint call, and the exact
  conditions under which an in-place memory decrease needs a restart.
- Any startup time or memory overhead figure for gVisor and for Kata
  Containers; the Kata figure quoted is the Kubernetes documentation's
  example.
- E2B's sandbox startup time and default timeout (the lifecycle page
  returned 404; the persistence and landing pages do not state them).
- Modal's startup time.
- CRIU's page listing what can be checkpointed (404); only the page listing
  what cannot was read.
- The Python `os` module page (truncated); the functions are cited from
  the local Python 3.14.4 docstrings.
- The template-level `parallelism` field of Argo Workflows and the Argo
  Server's per-action capabilities (not on the pages read).
- Temporal's runtime tuning page did not show slot defaults; they come
  from the tuning reference page.
- Per-task overhead figures for Ray, Dask, Celery, and Temporal (none
  documented on the pages read).
- OpenCost's allocation keys and its Cloud Native Computing Foundation
  status (not stated on the page read).
- The memory and start time of the OpenCode, Codex, and Pi processes as
  solutioning nodes (not measured).
- The first fetch of the systemd-run page at freedesktop.org returned 403;
  the man7.org copy was used instead.

## Sources read on 2026-09-18

Each entry gives the address, the date read, and the outcome.

- [Considerations for large clusters](https://kubernetes.io/docs/setup/best-practices/cluster-large/), 2026-09-18, read.
- [Pod overhead](https://kubernetes.io/docs/concepts/scheduling-eviction/pod-overhead/), 2026-09-18, read.
- [RuntimeClass](https://kubernetes.io/docs/concepts/containers/runtime-class/), 2026-09-18, read.
- [Resource quotas](https://kubernetes.io/docs/concepts/policy/resource-quotas/), 2026-09-18, read.
- [Limit ranges](https://kubernetes.io/docs/concepts/policy/limit-range/), 2026-09-18, read.
- [Jobs (concepts)](https://kubernetes.io/docs/concepts/workloads/controllers/job/), 2026-09-18, fetched twice, truncated before the completion mode and suspension sections.
- [Job field reference](https://kubernetes.io/docs/reference/kubernetes-api/workload-resources/job-v1/), 2026-09-18, read.
- [Indexed Job for parallel processing with static work assignment](https://kubernetes.io/docs/tasks/job/indexed-parallel-processing-static/), 2026-09-18, read.
- [Introducing suspended Jobs (2021 blog post)](https://kubernetes.io/blog/2021/04/12/introducing-suspended-jobs/), 2026-09-18, read; sentences paraphrased.
- [Horizontal Pod Autoscaling](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/), 2026-09-18, read.
- [Node autoscaling](https://kubernetes.io/docs/concepts/cluster-administration/cluster-autoscaling/), 2026-09-18, read.
- [Cluster Autoscaler frequently asked questions](https://github.com/kubernetes/autoscaler/blob/master/cluster-autoscaler/FAQ.md), 2026-09-18, read.
- [Karpenter NodePools](https://karpenter.sh/docs/concepts/nodepools/), 2026-09-18, read.
- [KEDA concepts](https://keda.sh/docs/latest/concepts/), 2026-09-18, read.
- [KEDA scaling Jobs](https://keda.sh/docs/latest/concepts/scaling-jobs/), 2026-09-18, read.
- [Kubelet checkpoint endpoint](https://kubernetes.io/docs/reference/node/kubelet-checkpoint-api/), 2026-09-18, read.
- [Feature gates](https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/), 2026-09-18, read.
- [Forensic container checkpointing in Kubernetes (2022 blog post)](https://kubernetes.io/blog/2022/12/05/forensic-container-checkpointing-alpha/), 2026-09-18, read.
- [Liveness, readiness, and startup probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/), 2026-09-18, read.
- [Pod lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/), 2026-09-18, read.
- [Node-pressure eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/), 2026-09-18, read.
- [Pod Quality of Service classes](https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/), 2026-09-18, read.
- [Resource management for Pods and Containers](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/), 2026-09-18, read.
- [Resize CPU and memory resources assigned to containers](https://kubernetes.io/docs/tasks/configure-pod-container/resize-container-resources/), 2026-09-18, read.
- [Pod priority and preemption](https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/), 2026-09-18, read.
- [Resource metrics pipeline](https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-metrics-pipeline/), 2026-09-18, read.
- [Pod startup latency service level objective](https://github.com/kubernetes/community/blob/master/sig-scalability/slos/pod_startup_latency.md), 2026-09-18, read.
- [Kueue concepts](https://kueue.sigs.k8s.io/docs/concepts/), 2026-09-18, read.
- [Kueue ClusterQueue](https://kueue.sigs.k8s.io/docs/concepts/cluster_queue/), 2026-09-18, read.
- [Kueue preemption](https://kueue.sigs.k8s.io/docs/concepts/preemption/), 2026-09-18, read.
- [Kueue: run a Kubernetes Job](https://kueue.sigs.k8s.io/docs/tasks/run/jobs/), 2026-09-18, read.
- [Kueue: monitor pending workloads on demand](https://kueue.sigs.k8s.io/docs/tasks/manage/monitor_pending_workloads/pending_workloads_on_demand/), 2026-09-18, read.
- [Argo Workflows: running at massive scale](https://argo-workflows.readthedocs.io/en/latest/running-at-massive-scale/), 2026-09-18, read.
- [Argo Workflows: parallelism](https://argo-workflows.readthedocs.io/en/latest/parallelism/), 2026-09-18, read.
- [Argo Workflows: scaling](https://argo-workflows.readthedocs.io/en/latest/scaling/), 2026-09-18, read.
- [Argo Workflows: synchronization](https://argo-workflows.readthedocs.io/en/latest/synchronization/), 2026-09-18, read.
- [Argo Workflows: architecture](https://argo-workflows.readthedocs.io/en/latest/architecture/), 2026-09-18, read.
- [Argo Workflows: field reference](https://argo-workflows.readthedocs.io/en/latest/fields/), 2026-09-18, read (workflow-level fields only).
- [Argo Workflows: Argo Server](https://argo-workflows.readthedocs.io/en/latest/argo-server/), 2026-09-18, read.
- [Volcano documentation](https://volcano.sh/en/docs/), 2026-09-18, read.
- [Ray tasks](https://docs.ray.io/en/latest/ray-core/tasks.html), 2026-09-18, read.
- [Ray actors](https://docs.ray.io/en/latest/ray-core/actors.html), 2026-09-18, read.
- [Ray resources](https://docs.ray.io/en/latest/ray-core/scheduling/resources.html), 2026-09-18, read.
- [Ray object spilling](https://docs.ray.io/en/latest/ray-core/objects/object-spilling.html), 2026-09-18, read.
- [Ray out-of-memory prevention](https://docs.ray.io/en/latest/ray-core/scheduling/ray-oom-prevention.html), 2026-09-18, read.
- [Ray actor fault tolerance](https://docs.ray.io/en/latest/ray-core/fault_tolerance/actors.html), 2026-09-18, read (a first address with a hyphen returned 404).
- [Ray cluster key concepts](https://docs.ray.io/en/latest/cluster/key-concepts.html), 2026-09-18, read.
- [KubeRay](https://docs.ray.io/en/latest/cluster/kubernetes/index.html), 2026-09-18, read.
- [KubeRay autoscaling](https://docs.ray.io/en/latest/cluster/kubernetes/user-guides/configuring-autoscaling.html), 2026-09-18, read.
- [Ray Dashboard](https://docs.ray.io/en/latest/ray-observability/getting-started.html), 2026-09-18, read.
- [Dask worker memory management](https://distributed.dask.org/en/stable/worker-memory.html), 2026-09-18, read.
- [Dask worker](https://distributed.dask.org/en/stable/worker.html), 2026-09-18, read.
- [Dask worker resources](https://distributed.dask.org/en/stable/resources.html), 2026-09-18, read.
- [Dask adaptive deployments](https://docs.dask.org/en/stable/adaptive.html), 2026-09-18, read.
- [Dask dashboard](https://docs.dask.org/en/stable/dashboard.html), 2026-09-18, read.
- [Celery workers guide](https://docs.celeryq.dev/en/stable/userguide/workers.html), 2026-09-18, read.
- [Celery tasks guide](https://docs.celeryq.dev/en/stable/userguide/tasks.html), 2026-09-18, read.
- [Flower](https://flower.readthedocs.io/en/latest/), 2026-09-18, read (index page only).
- [Temporal workflows](https://docs.temporal.io/workflows), 2026-09-18, read.
- [Temporal activities](https://docs.temporal.io/activities), 2026-09-18, read.
- [Temporal: detecting activity failures](https://docs.temporal.io/encyclopedia/detecting-activity-failures), 2026-09-18, read.
- [Temporal workers](https://docs.temporal.io/workers), 2026-09-18, read.
- [Temporal worker performance](https://docs.temporal.io/develop/worker-performance), 2026-09-18, read.
- [Temporal worker runtime tuning](https://docs.temporal.io/develop/worker-performance/runtime-tuning), 2026-09-18, read.
- [Temporal worker tuning reference](https://docs.temporal.io/develop/worker-tuning-reference), 2026-09-18, read.
- [Temporal activity commands](https://docs.temporal.io/cli/activity), 2026-09-18, read.
- [Temporal web interface](https://docs.temporal.io/web-ui), 2026-09-18, read.
- [gVisor documentation](https://gvisor.dev/docs/), 2026-09-18, read.
- [gVisor platforms](https://gvisor.dev/docs/architecture_guide/platforms/), 2026-09-18, read.
- [gVisor performance](https://gvisor.dev/docs/architecture_guide/performance/), 2026-09-18, read; no numeric figures captured.
- [Kata Containers architecture](https://github.com/kata-containers/kata-containers/blob/main/docs/design/architecture/README.md), 2026-09-18, read.
- [Firecracker README](https://github.com/firecracker-microvm/firecracker/blob/main/README.md), 2026-09-18, read; it points to the specification.
- [Firecracker specification](https://github.com/firecracker-microvm/firecracker/blob/main/SPECIFICATION.md), 2026-09-18, read.
- [E2B documentation](https://docs.e2b.dev/), 2026-09-18, read after a redirect from `e2b.dev/docs`.
- [E2B sandbox persistence](https://docs.e2b.dev/sandbox/persistence), 2026-09-18, read after a redirect.
- [E2B sandbox lifecycle](https://docs.e2b.dev/sandbox/lifecycle), 2026-09-18, 404.
- [E2B site](https://e2b.dev/), 2026-09-18, read.
- [Modal sandboxes](https://modal.com/docs/guide/sandbox), 2026-09-18, read.
- [Modal sandbox snapshots](https://modal.com/docs/guide/sandbox-snapshots), 2026-09-18, read.
- [Modal security](https://modal.com/docs/guide/security), 2026-09-18, read.
- [Pressure stall information](https://docs.kernel.org/accounting/psi.html), 2026-09-18, read.
- [Control group version 2](https://docs.kernel.org/admin-guide/cgroup-v2.html), 2026-09-18, read.
- [proc_meminfo manual page](https://man7.org/linux/man-pages/man5/proc_meminfo.5.html), 2026-09-18, read.
- [systemd-run manual page (freedesktop.org)](https://www.freedesktop.org/software/systemd/man/latest/systemd-run.html), 2026-09-18, 403.
- [systemd-run manual page (man7.org)](https://man7.org/linux/man-pages/man1/systemd-run.1.html), 2026-09-18, read.
- [systemd.resource-control manual page](https://man7.org/linux/man-pages/man5/systemd.resource-control.5.html), 2026-09-18, read.
- [signal manual page](https://man7.org/linux/man-pages/man7/signal.7.html), 2026-09-18, read.
- [docker pause](https://docs.docker.com/reference/cli/docker/container/pause/), 2026-09-18, read.
- [podman container checkpoint](https://docs.podman.io/en/latest/markdown/podman-container-checkpoint.1.html), 2026-09-18, read.
- [CRIU main page](https://criu.org/Main_Page), 2026-09-18, read.
- [CRIU: what can be checkpointed](https://criu.org/What_can_be_checkpointed), 2026-09-18, 404.
- [CRIU: what cannot be checkpointed](https://criu.org/What_cannot_be_checkpointed), 2026-09-18, read.
- [CRIU: TCP connection](https://criu.org/TCP_connection), 2026-09-18, read.
- [Python os module](https://docs.python.org/3/library/os.html), 2026-09-18, fetched but truncated before the process functions.
- [Python resource module](https://docs.python.org/3/library/resource.html), 2026-09-18, read.
- [Python signal module](https://docs.python.org/3/library/signal.html), 2026-09-18, read.
- [Python subprocess module](https://docs.python.org/3/library/subprocess.html), 2026-09-18, read.
- [psutil documentation (latest)](https://psutil.readthedocs.io/en/latest/), 2026-09-18, fetch failed.
- [psutil documentation (stable)](https://psutil.readthedocs.io/en/stable/), 2026-09-18, read.
- [OpenCost documentation](https://www.opencost.io/docs/), 2026-09-18, read.
