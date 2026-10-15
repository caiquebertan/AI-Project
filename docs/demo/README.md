# Demo: web and Android talking through the real server

`web-android-interop.mov` (40 s, screen recording of the operator's Mac, 2026-10-14 21:34). **Human-validated by the operator.**

What it shows, left to right: the generated web client in Chrome (`localhost:5173`, user `bob`) and the generated Android client in the Android Studio emulator (Medium Phone API 37.0, user `alice`), both against the local Python server.

- Both clients open the conversation with the other user and send messages in both directions; each message appears as Sent on the sender's side and Received on the other, with the local time.
- Bob turns on **Offline mode** in the web client and sends "Im working": it shows **Pending** while offline.
- Bob goes back online; the message is delivered and appears on Alice's emulator.

This is a manual run, not the automated interop suite (`tests/interop/`, in FUTURE.md). The generated code is the unmodified output of `/generate` (commits `78dd1bf` web, `796718d` Android).
