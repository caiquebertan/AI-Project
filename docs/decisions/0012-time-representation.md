# 0012 — Time representation: UTC everywhere, local zone only for display
- Status: proposed (awaiting G0)
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
