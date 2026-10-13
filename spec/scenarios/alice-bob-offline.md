# Scenario: Alice and Bob offline/reconnect

Source: brief, "Required behavior". Both clients MUST produce identical observable states at every step.

| # | Action | Expected server mailbox state | Expected Alice view | Expected Bob view |
|---|---|---|---|---|
| 1 | Alice → Bob: "Hi Bob, I have something important to tell you" | ☐ | ☐ | ☐ |
| 2 | Bob → Alice: "What is it?" | ☐ | ☐ | ☐ |
| 3 | Alice goes offline, queues a message | ☐ | ☐ | ☐ |
| 4 | Bob goes offline, queues a message | ☐ | ☐ | ☐ |
| 5 | Alice reconnects; her queued message reaches the server | ☐ | ☐ | ☐ |
| 6 | Alice goes offline again | ☐ | ☐ | ☐ |
| 7 | Bob reconnects; receives Alice's message and delivers his own queued message | ☐ | ☐ | ☐ |

The texts of the queued messages in steps 3 and 4 are not given in the brief; the spec MUST fix them for test purposes (☐ TBD).

Open questions to resolve in the spec:
- After step 7, does Alice (offline) see Bob's message only once she reconnects again?
- Final ordering of the four+ messages in each user's view.
