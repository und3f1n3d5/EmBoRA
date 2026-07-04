# Short note for article/revision use

The corrected code introduces an explicit implementation-status boundary that matches article v11. In `reported_runs_compat`, adapter/appraisal variables are diagnostic/explanatory and should be described as reconstructed or logged diagnostics. In `integrated_model`, the same adapter/appraisal layer is behavior-driving and belongs to the next architecture version.

Direct comparison with v11 reported tables should use only `reported_runs_compat` runs. `integrated_model` runs can be used to support the roadmap: white-box traces, ablations, validation of adapter proxies, and testing whether state degradation remains after removing artificial appraisal/update errors.

The most important methodological change is the delta-based ОТС/appraisal. The previous failure mode was that an agent could receive a negative reaction simply because a value had not yet reached its desired target. The corrected logic uses actual value changes: improvement is positive, loss is negative, and no change is neutral.

The runner now records `model_mode`, behavior-driving flags, focal-agent adapter arguments, decision traces, duplicate-observe checks, fallback flags and manifests. This makes future results easier to audit and safer to cite.
