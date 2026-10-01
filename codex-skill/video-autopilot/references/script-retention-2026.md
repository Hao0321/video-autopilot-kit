# 腳本三支柱＋留存節奏（public calibration guide）

> **PUBLIC_FIXTURE / privacy boundary:** no maintainer transcript, sample count,
> dated evaluation, speaking-rate measurement or private voice quote is included.

三支柱是語氣、觀眾語言與留存節奏。語氣從使用者自己的 voice profile 讀取；
觀眾語言與節奏由 `src/longform_maker/script_gate.py` 提供 generic starter checks。

## 支柱 1：創作者自己的語氣與邏輯

先由使用者提供或授權讀取至少兩篇**同片型、同敘事模式**的本人原稿，保留來源、版本和使用範圍。草稿逐段比對：是否採用本人常用的第一人稱視角、現場帶看方式、能量與幽默，是否真的回答觀眾當下的問題；不要靠重複招牌詞、驚嘆號或通用留存公式假扮語氣。`script_gate` 的 PASS 不能標成 voice PASS。若缺同模式樣本，只能標 `VOICE_REVIEW_REQUIRED`。

寫稿前固定觀眾承諾、真素材證據與可宣稱的功能；缺畫面或尚未完成的成果標 `ASSET_REQUIRED`，不能寫成已完成。觀眾旁白講清楚操作、結果與前後因果；內部驗證項目留在製作表。人工評分和修正只適用其綁定的影片及版本，不能挪作另一支片的評價。

剪輯計畫同時檢查語意相符的畫面數量、動作連續、跨鏡頭調色、音樂連續與有理由的轉場；機械 QA 通過不代表審美通過。個人聲紋、原稿、素材和私人診斷器應保留在受保護的 creator profile，不進公開發行包。

## 支柱 2：觀眾語言

公開版四層詞表只是示範結構：

| 層 | 用途 |
|---|---|
| SPOKEN_OK | 已由使用者自己的逐字稿或受眾研究證明可直接使用 |
| SUBSTITUTE | 有更清楚本地語言時，要求換成白話 |
| NEED_PAIR | 術語可以出現，但同一 beat 必須附白話解釋 |
| HARD_BAN | 內部工程詞不進旁白 |

新詞先以 warning 出現，再由人工依自有逐字稿判級。不要把公開 starter list
宣稱成任何特定創作者的受眾證據。

## 支柱 3：留存節奏

- cold open 先給結果或懸念，不用自介拖延。
- 每個中段 beat 要有問題、轉折或新 payoff。
- 長 beat 應拆段，並穿插短句打點。
- re-hook 與 pattern interrupt 的落點依實際字速與片長計算。
- 片尾只保留一個主要動作，並把已開的 loop 關完。

所有字速、句長和時間門檻都是可覆寫的 starter defaults。先用自己的錄音量測，
再將 profile、樣本範圍與變更理由寫入 evidence ledger。

## 交付流程

載入 creator profile 與同模式原稿 → 鎖定證據／宣稱 → 起稿 → 逐段原稿比較 →
精簡 → 跑 `script_gate.gate(text)` → 人工處理 warnings 與語氣偏差 → 錄音。
只有使用者自己的 transcript/evaluation 能升級為其預設值。
