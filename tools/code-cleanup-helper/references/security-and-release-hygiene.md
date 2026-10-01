# Security and release hygiene audit

這是 read-only repository evidence，不是滲透測試，也不把混淆等同安全。

## Anti-unpack boundary

使用者端桌面 binary 不可能保證永遠不能被解包、除錯或攔截。Cleanup 能要求的可驗證 hygiene 是：

- production bundle 不產 source map、PDB、TypeScript／Rust source 或 `sourceMappingURL`；minification 只增加閱讀成本，不是信任邊界；
- repository、build receipt、SBOM、log、archive 與 installer 不含私鑰、token、credential-shaped bytes、私人絕對路徑；
- executable／DLL 集合是 closed-world allowlist，未知 native payload 不因「能安裝」而通過；
- owner-only／restricted pack 在 manifest 與實際 installer 保持 fail-closed public redistribution metadata；
- 真正需要 entitlement 的素材用登入後下載、短期 URL、OS credential vault 與可撤銷授權；把共用解密 key 嵌進 client 不算保護。

靜態 source 只能判讀設定。若沒有解開實際 installer 的 project-native gate，把 delivered payload hygiene 標 `NOT_CHECKED`，不可從 `dist/` 或 build-directory executable 推定。

## High-risk repository findings

優先找：

1. Production 路徑接受環境變數替換 Node、FFmpeg、native core、helper executable、update installer 或允許 unsigned update。Debug-only override 必須有可測的 compile／packaged guard，不能只靠文件約定。
2. Update 只有 checksum、subject substring 或 manifest flag，卻沒有 credential-free HTTPS、bounded download、SHA-256、精確 signer subject、certificate fingerprint、user consent、transaction 與 rollback。
3. Electron／WebView preload 暴露 generic IPC、未驗證 sender、允許 navigation／new window／permission，或 custom media protocol 能讀任意 absolute path。
4. MCP／agent 只做 lexical `..` 檢查，卻沒用 realpath 阻擋 symlink／junction escape；project、media 與 output 三條路徑都要覆蓋。
5. Remote control 把 bootstrap 放 query、比較 token 用普通 equality、POST 不驗 Origin／Fetch Metadata／content-type、沒有 pairing rate limit、CSP 依賴 `unsafe-inline`、錯誤回傳本機 path，或 HTTP server 沒有 body／request／header bounds。若宣稱「QR 掃一次永久綁定」，另查是否只是延長記憶體 session、host 是否明文保存長效 credential、同 device 重配是否旋轉、停止 Remote 是否誤撤銷、以及是否缺少單裝置 revoke。
   永久授權不等於跨網可達；LAN-only host、隨機 Quick Tunnel 或每次改 hostname 都不能關閉不同網路承諾。跨網拓撲應讓桌機與手機主動連到 owned stable HTTPS/WSS relay，並分開驗證 relay deployment 與 device authorization。手機 raw 長效 credential 應在 HttpOnly／Secure／SameSite cookie 或 OS vault，不得進 URL、LocalStorage／SessionStorage、log、receipt、worker source 或 installer config；relay socket/session 仍須回查 host-side revoke，不能只因連線存活就永久授權。
6. Internal package 和 public package 共用同一資源清單，導致 owner-only music／model／dataset 可被公開 build 誤包。
7. Release 宣稱使用 pinned Node／Python／toolchain，卻只把目錄 prepend 到 `PATH`；Windows `npm.cmd` 等 wrapper 仍可能呼叫自己旁邊的舊 runtime。若沒有版本、相對來源與 executable SHA-256 的 build receipt，建置器身分仍是 `NOT_CHECKED`。
8. Session-native AI 整合要求使用者把 OpenAI／Anthropic API key、OAuth／訂閱 token 或 credential dump 貼進 editor。Local STDIO MCP 的產品設定只應保存非秘密的 executable、args、workspace／runtime paths；AI 登入與用量留在 Codex／Claude host。檢查 clipboard fallback、IPC payload、MCP init instructions、log、crash dump、config fixture 與 installer text，並以 secret-shaped negative fixture 證明不會把 host 環境中的 provider credential 複製進產品設定。

找到這些模式時，Cleanup 可回報 source-level `FAIL`／`REVIEW`；若實際行為仍需 runtime 才能證明，在建議中明確交給 R&D gate。

## Required project-native evidence

Promotion 至少要有：

- evaluator 的正控制，以及每種風險一個會真的阻擋的 negative fixture；
- 用固定 identity 解包工具檢查 actual installer／archive entries 與 text payload；
- delivered PE／Mach-O 的 architecture、version、signing 與平台 exploit mitigations；Windows 至少檢查 ASLR、NX、High Entropy VA；
- public profile 對 unsigned artifact 與 restricted pack 的負向拒絕；
- Remote 的跨站、缺 Origin、錯 content-type、錯 token、rate-limit、cookie、CSP 與 private-path negative requests；
- 永久裝置綁定要有短效 QR → 獨立高熵 device credential 交換、host 只存單向 hash、service／app restart 無 QR 重連、stop 保留信任、單裝置 revoke 後舊 credential 立即 401，以及 URL／log／receipt／installer 無長效 credential 的正負 journey；
- 不同網路 Remote 要另有 desktop outbound WSS、mobile outbound WSS、owned stable origin、bounded relay envelope、HTTP claim Origin/size/CSP controls 與真實撤銷 journey；本機 relay/DO smoke 只能證明協定，未部署 DNS／TLS／provider identity 或未跑 5G-to-desktop 真機時保留外部 blocker。部署前先驗 cloud account、domain/zone ownership 和實際 write scope，避免把權限錯誤誤報成已上線。
- 同一套交付旅程的合法 mutation probe 也必須送出符合新政策的同源 Origin／JSON headers；安全強化後只剩負測通過、正向 journey 因舊 client 被 403 擋下，不算 promotion；
- MCP 的 symlink／junction escape fixture；
- session-native MCP 的隔離 host-config journey：暫時的 Codex／Claude 設定目錄、含空白路徑、重複安裝／更新、CLI 缺失 fallback，以及設定檔中無 AI key／token；
- wrapper 必須保留失敗 child 的 stderr，若 stderr 空白則保留 bounded stdout／machine receipt，不能只留下 exit code；
- 真正執行 compile／bundle 子程序的 runtime 必須產生 build receipt（version、bundle-owned source、executable SHA-256），receipt 要進 input identity／embedded manifest；以呼叫 evidence script 當下的 `process.version` 代替建置時身分不可通過；
- final mutation 後重新比對 build receipt、artifact evidence 與 Cleanup promotion freshness。

Mixed-language repository 若回報 `cross-language-architecture-not-checked`，不得靠降低 `--require-checked` 後把整體架構宣稱成已驗證。保留 Cleanup 的 `NOT_CHECKED`，並以產品原生的 TypeScript／Rust import graph、cycle、layer／boundary gate 補足；兩份 evidence 要分開命名、分開要求，而且 native gate 不能改寫 provider 原本的判定。Promotion 只可要求 Cleanup 真正量測到的維度，同時把 native architecture gate 列為獨立必要條件。

遇到 `file-long`／responsibility hotspot，不得先提高全域行數門檻來消除 finding。優先抽離具名責任（例如 presentation wiring、event handlers、transport adapter），維持原門檻並重跑 typecheck、unit tests、架構 gate 與 delivered UI journey；只有在有 corpus 證據顯示 evaluator 系統性誤判時才校準門檻，且必須保留原案例作 regression fixture。

Evidence CLI 的 option value（例如 `--output report.json`）不得再被 positional-target 掃描器當成 audit root。Self-test 至少要覆蓋「只給 option＋value、沒有顯式 target」以及「target＋option＋value」兩種排列；產出 evidence 後再檢查報告內的 target identity，而不是只信 exit code 或檔案存在。若外層 wrapper／transpiler CLI 會先消費同名旗標，改用不攔截 argv 的明確 runtime 入口（例如 pinned Node `--import` loader）或經校準的 `--` separator，並保存 child 實際 argv；只修應用 parser 不能關閉 wrapper-level argument loss。

沒有 code-signing identity、Apple notarization、正式 HTTPS channel、真機或授權 provenance 是外部 blocker，不可用本地假憑證、self-signed demo 或「已混淆」升級成 PASS。
