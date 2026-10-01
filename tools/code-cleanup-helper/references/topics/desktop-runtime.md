# Desktop runtime and background-job audit

- `cleanup.desktop.nonblocking-job`: update checks, downloads, models, analysis, and renders return an immediate bounded state and execute off the UI/WebView thread. While delayed, an independent UI probe must remain responsive.
- `cleanup.desktop.owned-controller`: automation uses an isolated profile and owned process/connection. A timed-out command invalidates only its owning socket; a replacement connection cannot inherit stale rejects.
- `cleanup.desktop.semantic-ready`: replace fixed sleeps and translated labels with bounded semantic readiness predicates, while preserving elapsed time, controller misses, child exit, and primary error evidence.
- `cleanup.desktop.durable-result`: coalesce duplicate jobs, publish results atomically, distinguish terminal failure/cancel/timeout, and prove retry cannot consume a stale result from another mode.
- `cleanup.desktop.isolated-state`: recovery files, update caches, credentials, batch sessions, and trusted-device stores must not touch the user's live profile in tests. Replay twice to expose leaked state.

Lifecycle acceptance uses a real owned navigation/close flow; synthetic `beforeunload` dispatch is not native-close evidence. Bundle byte ceilings are exact gates and cannot be raised merely to erase a regression.
