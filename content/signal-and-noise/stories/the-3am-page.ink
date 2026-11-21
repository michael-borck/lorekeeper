VAR evidence = 0
VAR containment = 0
VAR trust = 0
VAR root_cause = false

-> start

=== start ===
It is 03:12. The phone on the desk lights up with a page from the monitoring service: the customer portal is timing out for some users. It is not down for everyone.

You are the only person awake. The incident channel has three messages and no decisions.

* [Open the incident channel and page the on-call engineer]
    ~ trust = trust + 1
    You open the channel, state the impact in one sentence and page the engineer. The response is immediate: "I'm here. What do we know?"
    -> triage
* [Restart the portal container first]
    ~ containment = containment + 1
    ~ evidence = evidence - 1
    You restart the portal. Some users reconnect. The logs from the failure disappear with the container.
    -> triage
* [Check the status page and go back to sleep]
    ~ trust = trust - 1
    You decide it is probably a blip. Twenty minutes later the page arrives again, and now the support lead is awake too.
    -> triage

=== triage ===
The support lead sends a screenshot: a booking form that never finishes. The monitoring graph shows normal CPU and plenty of free memory. The proxy is still serving other routes.

You have three things you can do before the next change.

* [Capture the proxy logs and the container state before changing anything]
    ~ evidence = evidence + 2
    You save the proxy log, the container state and the current network connections. It takes four minutes. The evidence is now yours.
    -> contain
* [Ask the support lead which customers are affected]
    ~ trust = trust + 1
    ~ evidence = evidence + 1
    The support lead names three customers on the same mobile network. That is a pattern, not a coincidence.
    -> contain
* [Roll back the last deployment immediately]
    ~ containment = containment + 1
    ~ evidence = evidence - 1
    The last deployment rolls back. The timeout rate drops. The failed request is gone, and so is the evidence you would need to explain it.
    -> contain

=== contain ===
The portal is still live, and the next failure is a matter of time. You need to stop the bleed without destroying the trail.

* [Put the proxy in maintenance mode and stop the bleed]
    ~ containment = containment + 1
    You switch the proxy to a clear maintenance page. Customers see an honest message instead of a dead form.
    -> diagnose
* [Keep it live and watch for the next failure]
    ~ trust = trust - 1
    You keep the service live and watch the graph. It fails again, and this time the support lead sees it before you do.
    -> diagnose

=== diagnose ===
{evidence >= 2:
    The evidence tells a story. A single upstream connection is being reused after it has already been closed. The proxy retries it forever, and the booking form waits.
    ~ root_cause = true
- else:
    You have a fix that makes the pain stop, but not a cause. The next failure will arrive with no explanation.
}

* [Write the incident note with what you know and what you do not]
    ~ trust = trust + 1
    -> ending
* [Close the incident because the service is up]
    ~ trust = trust - 1
    -> ending
* [Escalate to the vendor and hand over the evidence]
    ~ trust = trust + 1
    -> ending

=== ending ===
{root_cause:
    -> ending_root
- else:
    {containment <= 1:
        -> ending_fragile
    - else:
        -> ending_unknown
    }
}

=== ending_root ===
# ENDING: Root cause found
You write the incident record: impact, timeline, evidence, cause and the one change that prevents a repeat. The support lead sends it to the customers before the morning shift.

The next failure is less likely because the next person has a trail to follow.

-> END

=== ending_unknown ===
# ENDING: Service restored, cause unknown
The service is stable and the customers are back. The incident record is thin: what you changed, not why it worked.

You have bought time. The next failure will start from zero again.

-> END

=== ending_fragile ===
# ENDING: Fragile fix
The portal is up, but the evidence is gone and the cause is still out there. Within a week the same timeout returns, and nobody can explain it.

The lesson is not "restart faster". It is "capture first".

-> END
