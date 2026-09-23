# Security assessment receipt contract

Cleanup 不下載／安裝／執行 scanner，也不把其輸出當命令。Project-native runner 在既有授權內留存 receipt/evidence；Cleanup 只做 bounded read-only 驗證。

```powershell
python scripts/check_security_assessment.py <target> --receipt .rd/security-assessment.json --format json
python scripts/check_security_assessment.py --self-test
```

Exit `0/1/3`=`GREEN/BLOCK/NOT_CHECKED`；只有 syntax 用 `2`。Malformed、duplicate-key、錯誤路徑或 >5 MiB receipt 皆輸出不反射輸入的 `BLOCK` report。

## Promotion receipt v2

Closed-world 頂層：`schemaVersion=2`、`assessmentId`、`recordedAt`、`target`、`authorization`、`dataHandling`、`plannedTaskIds`、`engines`、`evidence`、`tasks`、`coverageClaim`。Receipt/engine support/calibration 時限為 24 小時／90 天／30 天。Integer 在 parse 前 bounded；float、NaN、Infinity、超出 signed 64-bit、duplicate key 或超結構限制皆拒絕。

Canonical JSON 使用 UTF-8、sorted keys、無空白、`ensure_ascii=false`；SHA-256 binding 為 lowercase hex，artifact/fingerprint 加 `sha256:`。Identity payload：`{"profile":"cleanup-security-target-identity/v1","product":<exact>,"version":<exact>}`。

### Live target snapshot

`target.product/version` 必須是 NFC Unicode，無 trim drift、category C（含 control/format/bidi）或 sensitive pattern；product ≤200 chars/512 UTF-8 bytes，version ≤128/256。另需 `snapshotProfile="cleanup-security-input/v1"`、canonical `snapshotSha256`、`snapshotManifestEvidenceId/Sha256`。`kind=snapshot-manifest` 的 entries 至少一筆；全空 target 不可 promotion。

Validator 以 bounded enumeration（第 20,001 個 object 在排序前拒絕）與固定 handle hash，比對 manifest exact membership/bytes/digest；included file 增刪改即 `BLOCK`。只排除固定 top-level roots：`.git`、`.rd`、`.cleanup-evidence`、`.mypy_cache`、`.pytest_cache`、`.venv`、`__pycache__`、`build`、`coverage`、`dist`、`node_modules`、`out`、`target`、`venv`，不得自訂。Symlink/reparse、ADS、control、Windows reserved/trailing-dot/trailing-space 與 superscript `COM`／`LPT` aliases 都 fail closed。上限為 20,000 files、單檔 64 MiB、合計 256 MiB。

### Exact authorization and plan

`authorization` 延續 v1 的 target IDs、activity tier、external contact、network／redirect／DNS／proxy、credential、destructive=false 與 request limits，另加：

- `planSha256`：綁 assessment/target/snapshot、完整 authorization、`plannedTaskIds`、每個 task 的 target/engine/planned checks，以及 exact engine version/revision/artifact/adapter/rules/data/fingerprint identity；集合先按 casefold 排序再 canonical hash。
- `authorizationEvidenceId`、`authorizationEvidenceSha256`：local-static 必須為 null；external contact 必須指向 `kind=authorization` 的 frozen JSON，內容逐欄等於 assessment ID、plan hash、targets、tier、canonical discrete host:port scope、authorizer、grant window、redirect/DNS/proxy、credential、destructive 與 limits。

Target ID 使用嚴格 `type:value` grammar，禁止 wildcard。External scope 只接受 canonical discrete host:port 或 `http(s)://`（URL 會 canonicalize 至 host:port）；CIDR、global wildcard、metadata/link-local IP、metadata hostname、userinfo、numeric-obfuscated host 都拒絕。Task 可用比 grant 更安全的 `credentialMode=none`。

v2 每個 authorized target 的 task union，須在 planned/executed IDs 完整含 `cleanup-security-control-coverage/v1` 六控制（scope、coverage、provenance、normalization、admission、adapter-integrity）。`controlCoverage` 計 cells；executed 僅算 terminal-complete。漏 plan=`BLOCK`，漏 run=`NOT_CHECKED`；防漏項，不證 scanner truth。

### Engine calibration

每個 admitted、referenced engine 增加 `calibrationEvidenceId`、`calibrationSha256`，指向 `kind=calibration`：

```text
schemaVersion, profile=cleanup-security-calibration/v1,
engineId, engineVersion, sourceRevision, artifactDigest,
adapterSha256, rulesSha256, dataSha256, fingerprintSchema,
fixtureSetSha256, calibratedAt, passedNegativeControlIds
```

Identity/evidence digest 須逐欄匹配。Required controls exact set：known finding detected、malformed output rejected、truncated output rejected、parser crash rejected、source drop rejected、duplicate source rejected。`manual-review` license 或 unadmitted engine 只能 `NOT_CHECKED`；未被 task 引用的 engine 拒絕。

### Adapter-result reconciliation

每個有 executed check 的 task 增加 `adapterResultEvidenceId`、`adapterResultSha256`，指向 `kind=adapter-result`：

```text
schemaVersion, profile=cleanup-security-adapter-result/v1,
taskId, rawEvidenceId, rawEvidenceSha256,
engineId, engineVersion, engineSourceRevision, engineArtifactDigest,
fingerprintSchema, adapterSha256, rulesSha256, dataSha256,
snapshotSha256, commandSha256, environmentSha256,
plannedCheckIds, executedCheckIds, exitCode, successMarker,
parserState, rawSourceObservationIds, rawSourceObservationCount,
normalizedFindings[{findingId,sourceObservationIds}],
truncationCount, unparsedCount
```

Envelope 的 snapshot、command、environment、planned/executed check arrays、child exit 與 success marker 必須逐欄精確等於 task/execution record；任一漂移都 `BLOCK`。`completed|findings` 只能搭配 `parserState=complete`、0 truncation、0 unparsed。Raw observation IDs 必須 unique、count 相等，而且每一筆恰好映射一次到 task finding；drop、duplicate、normalized-to-zero、finding-ID drift 都 `BLOCK`。Raw evidence 必須非空且一個 raw ID 不得供多 task 使用。自行標成 `resolved`／`false_positive` 沒有獨立 waiver/retest trust 時仍 `NOT_CHECKED`。Timeout/cancel 可保留 null exit；誠實 `not_tested` 可省略 execution，但 aggregate 只能 `NOT_CHECKED`。

Task-owned evidence 加 adapter result 的實際 file count、bytes、relative depth不得超過 execution 宣告的 `outputFiles/outputBytes/outputDepth`。所有 v2 evidence 固定在 `.rd/security-evidence/`；registry 必須與 snapshot／grant／calibration／adapter／task 的 exact single ownership 相等，禁止 unused 或跨 task 共用 evidence。

## Evidence and report safety

Registry 上限 512 files、單檔/合計 256 MiB；JSON 另有 ceiling。檔案以同一 handle bounded read/hash，pre/post stat 防替換。輸入皆不可信；finding 只輸出固定 status/code/message。Report 不輸出 product/version 明文，只輸出 domain-separated digest；machine fields 限 timestamp/digest、boolean、count。

GREEN report 會提供 `receiptSchemaVersion=2`、canonical `recordedAt`、`ageSeconds`、target `identityProfile="cleanup-security-target-identity/v1"`、`identitySha256`、`snapshotProfile/snapshotSha256/snapshotVerified`，以及 authorization `externalContact/planSha256/frozenGrantSha256`，供 completion gate 再施加更嚴格 policy。無法解析 receipt 的 input-error report 保留相同 target keys，但 identity、snapshot digest/profile 都是 null、`snapshotVerified=false`。

## v1 compatibility and decisions

v1 仍解析且錯誤可 `BLOCK`；即使有效也至少 `NOT_CHECKED`＋`legacy-unbound-security-receipt`，永不 promotion `GREEN`。

- `BLOCK`：schema、live snapshot、plan/grant、hash、scope、calibration、adapter reconciliation、ownership、isolation或 count 不一致，或有 open finding。
- `NOT_CHECKED`：v1、過期 receipt/knowledge、partial/failed/timed-out/cancelled task、unadmitted engine 或 manual-review license。成功 sibling 保留，但 aggregate 不全綠。
- `GREEN`：v2、fresh、live snapshot exact、plan/grant/calibration/adapter/evidence 全部閉合、所有 planned checks complete 且 0 open finding。零 finding 或 exit 0 單獨永遠不夠，也不是 compliance certification。

這個 contract 證明 validator 當下看到的 local bytes、receipt 與 frozen evidence 自洽；它不憑空建立 authorizer 公鑰、CI signer 或 transparency-log trust。需要獨立來源認證的發行流程，仍須在外層用簽章／attestation policy 綁住 receipt digest。

本契約由我們獨立實作；設計 review 參考社群專案 `teddashh/ai-security-scanner` 的 Apache-2.0 repository，固定研究 revision `fd9194f285f3ffae8236fc7b8b30e1a611fe722a`，未複製其程式碼或 schema。
