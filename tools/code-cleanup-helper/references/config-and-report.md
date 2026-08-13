# Audit config 與 report schema

在目標根目錄建立 `audit.config.json`。不用 YAML，避免 PyYAML 依賴與 Windows 環境差異。

```json
{
  "exclude": [".git/**", "node_modules/**", "private/**"],
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
    "max_module_out_degree": 18,
    "max_module_fan_in": 24,
    "duplicate_function_min_lines": 8,
    "duplicate_function_min_nodes": 24
  }
}
```

`drift_assertions` 的 `pattern` 是 Python regex；`files` 使用 glob；`expected_count` 預設 0。把穩定、可機械驗證的事實放這裡，不把分析推論硬寫成 assertion。`required_dependencies` 是量測校準 gate：預期 edge 消失時直接 FAIL，適合保護關鍵資料路徑，不用來強迫所有模組互相依賴。

JSON report 欄位：

- `schema_version`：報告格式版本。
- `target／mode／config`：執行範圍。
- `summary`：files、lines、bytes、PASS、FAIL、REVIEW、NOT_CHECKED。
- `inventory`：每檔行數、bytes、SHA-256。
- `architecture`：module／edge、SCC cycles、layer violations、forbidden／missing-required edges、hotspots、long functions、duplicate function bodies 與 parse errors。
- `findings`：dimension、status、code、message、path、line、details。

`details` 是機器可讀證據；人類報告只顯示前 N 筆，避免把 terminal 塞滿。
