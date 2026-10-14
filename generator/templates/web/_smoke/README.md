# Smoke app (session A, token-free)

Used only by `apply_templates.py --smoke` / `smoke_build.py`; never copied into `clients/`. A minimal app, one
node-environment test and one jsdom component test; titles start with a spec id so the run also checks that ids
reach `test-results/junit.xml`. `npm install` here creates the `package-lock.json` that is then committed to
`generator/templates/web/`. Generator design §2.4, §5.
