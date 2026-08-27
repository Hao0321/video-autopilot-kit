# Audit config 與 report schema

在目標根目錄建立 `audit.config.json`。不用 YAML，避免 PyYAML 依賴與 Windows 環境差異。

```json
{
  "exclude": [".git/**", "node_modules/**", "runtime-secrets/**"],
  "length_exceptions": ["references/generated-index.md"],
  "navigation_exceptions": ["references/cases/case-*.md"],
  "id_definition_scopes": {
    "R": ["references/rules/R*.md"],
    "F": ["references/formulas.md"],
    "CASE": ["references/cases/case-*.md"]
  },
  "range_claim_scopes": {
    "R": ["references/rules.md"],
    "F": ["references/formulas-index.md"],
    "CASE": ["references/case_studies.md"]
  },
  "thresholds": {
    "skill_warning": 200,
    "skill_severe": 400,
    "reference_warning": 400,
    "reference_severe": 800,
    "code_warning": 500,
    "code_severe": 1000
  },
  "sync": {
    "public_root": null,
    "ignore": ["style_profile.md", "content_plan.md", "data/**"]
  },
  "drift_assertions": [
    {
      "id": "forbid-old-sample-count",
      "files": ["SKILL.md"],
      "pattern": "AI 短劇.*n=1",
      "expected_count": 0,
      "message": "AI 短劇速查仍保留舊 n=1"
    }
  ],
  "artifact_set_assertions": [
    {
      "id": "generated-product-images",
      "left_glob": "public/images/products/ads/*.webp",
      "right_glob": "private/supplier-catalog/*.webp",
      "key_pattern": "^(a\\d{3})\\.webp$",
      "expected_count": 175,
      "left_min_bytes": 20000,
      "right_min_bytes": 5000,
      "forbid_globs": ["private/supplier-catalog/*.png", "public/images/products/supplier/**"],
      "message": "公開商品商攝與私有供應商原圖不是一對一，來源圖落入 public，或仍有未清理／異常資產"
    }
  ],
  "privacy": {
    "tokens": ["C:/Users/作者名", "私人品牌詞"],
    "allow": ["private/**"]
  },
  "architecture": {
    "enabled": true,
    "layers": [
      {"name": "domain", "patterns": ["domain/**"], "may_depend_on": []},
      {"name": "application", "patterns": ["application/**"], "may_depend_on": ["domain"]},
      {"name": "interface", "patterns": ["cli/**", "api/**"], "may_depend_on": ["application", "domain"]}
    ],
    "forbidden_dependencies": [
      {"source": "domain/**", "target": "cli/**", "message": "Domain 不可反向依賴 CLI"}
    ],
    "required_dependencies": [
      {"source": "cli/log_outcome.py", "target": "storage/store.py", "message": "寫入器必須經過鎖與 revision guard"}
    ],
    "ignore_edges": [],
    "function_warning_lines": 80,
    "function_severe_lines": 160,
    "function_exceptions": [
      {
        "path": "cli/legacy.py",
        "name": "run_linear_gate",
        "max_lines": 130,
        "reason": "線性驗收步驟拆分後反而降低可讀性",
        "expires_on": "2026-12-31"
      }
    ],
    "module_hotspot_exceptions": [
      {
        "path": "foundation/project_paths.py",
        "max_fan_in": 30,
        "max_out_degree": 2,
        "reason": "穩定、無副作用的基礎模組；集中共用比複製路徑規則安全",
        "expires_on": "2026-12-31"
      }
    ],
    "max_module_out_degree": 18,
    "max_module_fan_in": 24,
    "duplicate_function_min_lines": 8,
    "duplicate_function_min_nodes": 24
  }
}
```

`drift_assertions` 的 `pattern` 是 Python regex；`files` 使用 glob；`expected_count` 預設 0。把穩定、可機械驗證的事實放這裡，不把分析推論硬寫成 assertion。`required_dependencies` 是量測校準 gate：預期 edge 消失時直接 FAIL，適合保護關鍵資料路徑，不用來強迫所有模組互相依賴。

`artifact_set_assertions` 的左右 glob、禁止 glob 都必須是 repo-relative POSIX path。每筆 assertion 必須有唯一非空 `id`、正整數 `expected_count`，且 `key_pattern` 至少含一個 capture group；pattern 對 basename 做 full-match，第一個 group 是 case-insensitive 配對 key。左右 glob 不得指到同一檔案，空集合、兩邊同時為空、兩側 key／數量不一致、最小 bytes、禁止檔、symlink 或重複 key任一不符即 FAIL。共用 `min_bytes` 可由 `left_min_bytes`／`right_min_bytes` 分別覆寫，避免把不同壓縮角色硬套同一門檻。通過或失敗時匹配到的二進位檔都納入 report inventory，讓 R&D freshness verifier 能偵測驗證後的 byte 變更。此量尺只證明集合完整與 bytes 新鮮，不證明圖片內容正確、色彩自然、介面實際顯示或商用權利。

生成圖與參考來源的配對不要求兩個角色都公開。當來源圖具有供應商授權、隱私或訓練輸入風險時，`right_glob` 應指向 web root 之外的私有目錄，並用 `forbid_globs` 明確禁止來源角色落入 `public／static／uploads`。不要把該私有來源目錄整體排除，否則 freshness inventory 無法鎖住來源 bytes。Cleanup 只能證明檔案位置與集合；公共 API 是否洩漏來源路徑、舊靜態 URL 是否 404、管理端是否驗證身分，必須交由 R&D 的 HTTP 正／負 journey gate。

第三方授權全文常會因多個字型／素材各自攜帶相同 OFL、MIT 或 Apache 文字而觸發重複段落。只可用精確角色 glob（例如 `public/fonts/*-OFL.txt`）把它們排除於結構重複／模組抽取量尺，並以另一個 closed-world rights／SBOM／delivery gate 逐檔鎖定 license bytes、來源與交付存在性。不可用 `*.txt`、`LICENSE*` 或整個素材目錄的廣域排除掩蓋自寫文件重複，也不可把 Cleanup 排除誤報成權利驗證通過。

`sync.normalize_text` 預設為 `true`：私公版同步與 `sync_public.py` 都忽略 UTF-8 BOM 及 LF／CRLF 差異，但仍偵測實際文字變更；設為 `false` 時才要求 byte-exact。二進位檔無法以 UTF-8 解碼時一律比較 bytes。

`module_hotspot_exceptions` 只適用於已確認穩定、低出度的基礎模組；每筆必須同時限制 `max_fan_in`、`max_out_degree`，並包含理由與到期日。有效例外仍輸出 `REVIEW`，超過任一上限或逾期立即恢復 `FAIL`，不可用來全域放寬量尺。

路徑 glob 一律以 repo-relative POSIX path 判斷；`**/folder/**` 表示任意深度，包含 target 根目錄正下方的 `folder/`。

JSON report 欄位：

- `schema_version`：報告格式版本。
- `target／mode／config`：執行範圍。
- `summary`：files、lines、bytes、PASS、FAIL、REVIEW、NOT_CHECKED。
- `inventory`：每檔行數、bytes、SHA-256。
- `architecture`：module／edge、SCC cycles、layer violations、forbidden／missing-required edges、hotspots、long functions、duplicate function bodies 與 parse errors。
- `findings`：dimension、status、code、message、path、line、details。

`details` 是機器可讀證據；人類報告只顯示前 N 筆，避免把 terminal 塞滿。

需要判斷兩份 audit 是否來自同一份 target bytes 時，使用 `check_audit_snapshot.py` 比較完整 inventory。不要只比較 summary counts：內容可以改變而檔案數、行數與 finding 數完全相同。
