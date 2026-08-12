# 發佈中樞、文案研究與舊片再製

## 一個成片只有一個發佈包

唯一入口固定是 `videos/_PUBLISH_HUB/START_HERE.md`。所有完成且通過 QA 的影片統一進入
`videos/_PUBLISH_HUB/READY/<format>/<ready|review|draft>/<content-id>_<slug>/`。每包固定包含：

- 已命名成片：同磁碟優先使用 hard link，不複製影片位元組。
- `發布文案_可複製.md`：標題、共用內文、Hashtag 與來源，全部可直接複製。
- `publish.json`：SHA-256、來源、題材、查證狀態、發布狀態與平台 URL。

發布後整包移到 `videos/_PUBLISH_HUB/PUBLISHED/`；不是另做一份副本。沒有 `publish.json`、SHA 不符或研究過期，不得宣稱發佈包完整。
每包必須正好只有一支成片，多檔直接 RED。新版 SHA 不同時，舊成片只能進
`videos/_archive/publish-hub-retired/<UTC>/<content-id>/`，並留下來源、去向、SHA-256 與 bytes 稽核。

## 命名

短片：`S021_榮耀女武神_vs_黃金神杖.mp4`。長片：`L001_主題名稱.mp4`。再製片：`R001_苗栗一日遊_4站.mp4`。檔名只放能辨識內容的資訊，版本由 `publish.json` 管，不使用 `final_final_v3`。
`publish.json` 另含 `artifact_revision`；`v2／FINAL／old／backup／初剪／draft` 類名稱一律禁止進發布包。

## 文案的兩層證據

1. 片內證據：主體、勝負、感受與發生順序，以 plan、畫面與使用者確認為準。
2. 外部研究：產品名稱、官方術語、地址、營業、價格、功能與熱門搜尋語，以最新官方來源優先；記錄 `last_verified` 和網址。

研究不可以覆蓋片內事實。查不到就用「本片實測／這一局／這次到訪」等有限敘述，不編造規格或評價。新題材沒有 catalog 或超過 TTL 時，包裹標為 `RESEARCH_REQUIRED`，先查證再發布。
每次 `publish sync` 另更新 `videos/_PUBLISH_HUB/_STATE/publish_research_queue.json`；未建立題材 catalog 或已過期的待發佈片會列入佇列，下一次製作文案時只研究這些項目，不把整個網路研究庫塞進 prompt。

活動 job 的 `_out` 若已存在 `current.mp4`，帶 `v2／FINAL／old／backup／初剪／draft` 的舊 render 不再留在工作目錄；`publish retire-versioned-renders --apply` 只會把這類衍生檔搬到具 SHA-256 稽核的 archive。原始拍攝素材、沒有 `current.mp4` 的檔案與長片 canonical source 不會自動移動。

## 戰鬥陀螺文案

- 正版對正版：標題、字幕與 HUD 直接寫兩顆陀螺名稱，不出現多餘的「正版」。
- 正版對非官方仿製品：明確標示身份；不提供仿製品購買資訊，也不把單局勝負寫成普遍性能結論。
- Hook 用具體結果或懸念，例如「誰先出界？」；結尾用能回答的問題，不寫空泛「你覺得呢」。
- 產品規格與型別只引用官方產品頁；繁中收藏名稱以 Hao 的確認為準。

## 已發佈素材的再製

已發佈不等於封存。系統按「同區域、同日／同旅程、至少三個不同站點、原始片段仍在」產生再製候選。再製必須回到原始片段重建 Hook、順序、字幕與節奏，禁止把已上字幕的 Shorts 直接串接。

苗栗一日遊首個候選使用 S015–S018 原始素材，依拍攝時間為：金榜麵館 → 烏嘎彥竹林 → 勝興車站 → 龍騰斷橋。這是新的四站路線敘事，不是四支舊片合併。

## 去重

只有 SHA-256 完全一致才是可自動處理的重複檔。先建立權威檔，再將相同磁碟的副本改成 hard link 或在發佈中樞驗證後退休舊路徑；保留稽核報告。不同轉碼、裁切或版本即使看似相同，也不得自動刪除。
