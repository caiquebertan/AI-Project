# Core client behavior (skeleton)

_To be written._ Must define observable behavior:

- **CORE-LOGIN** — first launch asks for a name; name persisted locally; subsequent launches skip login.
- **CORE-SEND** — compose text to a named recipient; message appears in local conversation immediately with a state (pending / sent).
- **CORE-OFFLINE** — while disconnected, sends are appended to a persistent local outbox in order.
- **CORE-FLUSH** — on reconnect, the outbox is sent in order; each message leaves the outbox only after server ack.
- **CORE-RECEIVE** — messages from server are displayed in the conversation in the specified order, including those queued server-side while offline.
- **CORE-ORDER** — conversation ordering rule (by server sequence? by timestamp?) so both clients render identically.
- **CORE-VISIBLE** — what exactly is visible after each step (per-user view of conversation).
