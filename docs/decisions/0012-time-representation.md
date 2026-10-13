# 0012 — Time representation: UTC everywhere, local zone only for display
- Status: proposed (awaiting G0); amended (operator, OM-0011)
- Date: 2026-10-13
- Author: TL (agent, claude-opus-5-5); principle decided by operator (OM-0010)
- Spec ids driven: `CORE-TIME-001`, `CORE-TIME-002`, `CORE-ENV-006`, `CORE-ENV-007` (wording only), `PLAT-HOOK-009`, `PLAT-HOOK-013`, `PLAT-ANDROID-026`..`028`, `PLAT-WEB-019`..`021`. Rules are in [`spec/core/protocol.md`](../../spec/core/protocol.md) §5.1 and Appendix A, and in [`spec/platform/`](../../spec/platform/).

## Context
Operator (OM-0010): "save the time in UTC, and each client gets the local device timezone and shows to the user in their local time". The PM is adding the visible behavior: a message with a `seq` shows `HH:mm` (24-hour), or `YYYY-MM-DD HH:mm` when its local date differs from the viewer's current local date; a pending message shows no time; time never affects order. Two clients on different platforms, in possibly different zones, must produce the same text for the same instant, zone and "now", and tests must be able to fix all three.

## Decision
1. Every instant (wire, store, snapshot, fixtures) is a UTC string `YYYY-MM-DDTHH:mm:ss.sssZ`. Conversion to local time happens only when display text is produced.
2. The displayed instant is the server's `accepted_at`, not the sender's `created_at`.
3. The zone comes from an injected `TimeZone` provider (`zoneId()`, `offsetMinutesAt(instant)`) and "now" from the injected `Clock`, read at each display. Local wall time = instant + offset at that instant; seconds are truncated.
4. Both clients build the text by hand from numeric fields with ASCII digits. They use no locale-dependent formatters.
5. Tests fix the zone and clock: in-project tests inject fakes; external web tests use Playwright `timezoneId` and `page.clock`; emulator tests use `-timezone`.

## Alternatives considered
- **Display `created_at` (the sender's clock).** It is the "time typed", but the sender's clock may be wrong (emulators often are), and it is out of step with display order: in the scenario Bob's B2 was typed before A2 yet is shown after it, so times would run backwards in the list. Both users would also see different times for the same message only if the sender's clock was off. Rejected; `accepted_at` comes from one clock and is monotonic with `seq`.
- **Local time with a numeric offset on the wire (`2026-10-13T12:00:01.010-03:00`).** It carries the sender's zone, which nobody needs, and it gives two spellings for one instant, which complicates equality checks (dedupe compares `created_at`) and fixtures. Rejected; only `Z`.
- **Epoch milliseconds as numbers.** Compact, but unreadable in fixtures and logs, and it breaks the existing string fields. Rejected.
- **Platform locale formatters (`DateTimeFormatter.ofLocalizedTime`, `toLocaleTimeString`, `Intl.DateTimeFormat`).** They follow the device locale: 12-hour clocks, non-ASCII digits, and ICU/CLDR versions that differ between JVM, Android and browsers. Identical output across the two clients could not be guaranteed. Rejected in favor of an explicit pattern built by hand.
- **Format with the zone name or abbreviation.** Abbreviations vary by locale and tz database version, and they change with DST. Not shown, so the output does not depend on DST naming.
- **Server sends a preformatted local time.** The server does not know the viewer's zone. Rejected.

## Consequences
- Clients must store `accepted_at` for every sequenced message (sent from the E3 response, received from E4). The client snapshot gains `accepted_at` and `time_text`.
- A zone change shows on the next display. Whether the screen re-renders on its own when the zone or the date changes is the PM's to define.
- DST is handled through `offsetMinutesAt(instant)`; tests use fixed fake offsets, so they do not depend on the tz database. Only Appendix A names IANA zones, for external tests.
- The two users may legitimately see different dates for the same message (Appendix A: Bob's `00:00` is on the next day).

## Brief constraint affected
None.

## Amendment (OM-0011)
Operator: "server will expect times to be sent in UTC as well, and we won't have any hardcoded local timezone. Each client will implement their function to get the local time based on UTC server time, therefore clients will send the message time in UTC to the server too".
1. **Strict on input.** The server rejects any `created_at` that is not the exact UTC form of CORE-HTTP-007 and a real calendar instant (valid month, valid day for the month including leap years, hour 00–23, minute and second 00–59, no leap second, no offset, no lowercase `z`, exactly three fraction digits) with `400 malformed_request`. The position of that error in CORE-ERR-002 does not change. The schema pattern `common.schema.json#/$defs/timestamp` encodes the same rule; `spec/core/schema/cases/timestamp.json` lists valid and invalid cases (CORE-HTTP-007, CORE-SRV-030).
2. **The server has no time zone.** It reads only its UTC clock for `accepted_at`, never converts, and treats `created_at` as an opaque string once the format is checked (CORE-SRV-031, CORE-SRV-037).
3. **No hardcoded zone anywhere in production code or configuration** (CORE-TIME-003). A client's only zone source is its `TimeZone` provider reading the device. Zone values in specs, fixtures and tests are injected fakes or test-runner options. Generated in-project tests scan production sources with a shared denylist (PLAT-HOOK-015, PLAT-ANDROID-030, PLAT-WEB-023).
4. Clients send `created_at` in UTC from the injected `Clock` (CORE-ENV-006). It is sent, stored and validated but never shown; the displayed instant is `accepted_at`, converted at display time (decision point 2 above, unchanged).
- Alternatives: accept any RFC 3339 instant and normalise it on the server. Rejected: two spellings for one instant break the byte equality in duplicate checks (CORE-SRV-034), and the operator asked for UTC end to end.
- Spec ids: `CORE-HTTP-007`, `CORE-ENV-006`, `CORE-TIME-003`, `CORE-ERR-002`, `CORE-SRV-030`, `CORE-SRV-031`, `CORE-SRV-037`, `PLAT-HOOK-015`, `PLAT-ANDROID-030`, `PLAT-WEB-023`.
