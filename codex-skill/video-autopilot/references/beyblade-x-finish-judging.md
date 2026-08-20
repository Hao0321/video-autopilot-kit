# BEYBLADE X 勝負判定與剪輯標示規範

更新：2026-08-14。Canonical ruleset：Takara Tomy 日本版。依據：

- [BEYBLADE X Regulation 第 12 版（2026 年 3 月）](https://beyblade.takaratomy.co.jp/beyblade-x/_image/regulation.pdf)
- [BX-23 官方說明書](https://beyblade.takaratomy.co.jp/beyblade-x/manual/BX-23_manual.pdf)

這份規範服務的是「判對，再做得帥」。剪輯不得從單張畫面、聲音大小、飛行方向或觀眾反應猜結果。

## 1. 四種正式 Finish

| 官方顯示 | 分數 | 成立條件 | 不成立的常見誤判 |
|---|---:|---|---|
| `XTREME FINISH +3` | 3 | 對手整顆進入 Xtreme Zone，且未回到 Battle Zone | 只擦到區域、只有部分進入、之後仍整顆旋轉著回場 |
| `OVER FINISH +2` | 2 | 對手整顆進入 Over Zone，且未回到 Battle Zone | 單純撞牆、彈高、進區後又旋轉回場 |
| `BURST FINISH +2` | 2 | 在自己的陀螺之前，對手的零件脫落並分離 | 只是飛出去、停止旋轉、外觀晃動；Grip Bit 單獨從 Battle Grip 脫離也不算 |
| `SPIN FINISH +1` | 1 | 勝方仍在 Battle Zone 旋轉，對手原旋轉方向的速度先歸零 | 只看誰晃得比較大、只看最後一張靜止畫面 |

一般單顆對戰以 4 分先取為預設；Finish 是「這一局的得分方式」，不是每次都直接贏完整場 Match。活動可採不同賽制，發布前以該活動規章為準。

## 2. 判定順序與邊界案例

1. 逐格或慢動作找出最先成立的 Finish 瞬間。
2. 多種 Finish 同時發生時是 `DRAW / REPLAY`，不可挑分數高的硬判。
3. 進入 Xtreme/Over Zone 或離開場地後，若陀螺仍整顆旋轉並回到 Battle Zone，先前的 Xtreme/Over/重賽判定取消，繼續對戰。
4. 場外位置不是規章定義的 Over/Xtreme Zone、畫面完全遮住關鍵瞬間，或無法確認誰先發生時，不得硬判；內部標 `REVIEW`，公開預覽只可寫「判定待確認」。
5. 若是正式活動，最終以現場 Judge 判決為準；影片不得用後製推翻裁判。

## 3. 英文術語差異

Hao 的 Takara Tomy 系列統一使用 `XTREME / OVER / BURST / SPIN FINISH`。Hasbro 國際規則常將 Over 稱 `Knock Out Finish`、Spin 稱 `Survivor Finish`，但同一支影片不得混用兩套命名。

## 4. 影片與發布規則

- 結果卡只顯示官方 Finish 名稱、分數與勝方名稱；不要再寫模糊的「飛出去」「爆掉」「KO」代替計分術語。
- 趣味口語可以說「撞飛了」，但計分 HUD 仍須使用 canonical label。
- 正版對正版只顯示雙方名稱；正版對盜版才標真偽。
- 含盜版陀螺的內容可借用 Finish 詞彙描述畫面，但發布文案須註明「趣味對戰／非官方賽事判定」，不可暗示符合官方比賽器材資格。
- 倒數固定 `3・2・1 Go Shoot！`；不得寫成「3・2・1 發射」。
- 勝負卡最多出現約 0.7-1.2 秒，搭配定格、慢動作回放或衝擊音；不能遮住陀螺與判定區。

## 5. 結構化證據

```json
{
  "battle_result": {
    "finish": "burst",
    "winner": "榮耀女武神",
    "human_verified": true,
    "evidence": {
      "sequence_reviewed": true,
      "confidence": 0.98,
      "first_event": "burst",
      "opponent_parts_separated": true,
      "simultaneous": false
    }
  }
}
```

`beyblade_x_rules.py` 會驗證 winner、分數、區域、回場、零件分離、先後順序、同時發生與信心門檻；`shorts_gate.py` S-V 會阻擋沒有證據、標籤與資料矛盾或混用 ruleset 的公開成片。

## 6. 實際審片口訣

「先看有沒有分離，再看整顆進哪一區、是否回場，最後看誰先停；看不清楚就不裝懂。」
