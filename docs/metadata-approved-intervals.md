# 核准 Contact 區間來源契約

## 2026-11-05 wide Excel 更新

使用者已確認新版 wide 規則，取代下方舊 sidecar 契約在新版 Excel 上的限制：全部實體支架及 Contact termination 一起取 min/max；單個 active TL 回 N、多個回 Y、沒有 TL 維持未知；Landmark 實際範圍照用，單點只擴張一次 ±100m。A:C、D:G、H:J 為獨立清單，K 僅控制 D:E 開閉端點。多個不同 Landmark 同時命中時，依使用者最新決定顯示全部不同名稱，以「 / 」分隔，狀態為matched並保留來源列與名稱集合。

`WideExcelEnrichmentProvider` 自動辨識完整 11 欄工作表，直接讀 Excel 並驗證 workbook SHA，不要求人工維護 sidecar。舊 7 欄 workbook 繼續使用下方 sidecar 契約。新版候選位於 `outputs/metadata-review-2026-11-05/wide-v3/candidates`；前期使用隔離config驗證，2026-11-05使用者批准後8檔已正式啟用，16 routes及npm dev真UI smoke通過。正式release見 `config/tov1050-metadata-release.json`，原檔及舊release備份見 `config/backups/2026-11-05-wide-v3-activation-01`。Wear 計算授權限制維持原狀。

## 以下為舊版 sidecar 契約及歷史啟用狀態

日期：2026-10-29；關聯 DAV-26／DAV-21。此功能只接入逐 scope 核准的實體區間，不把 review workbook 的候選或空白批准欄視為授權。

使用者同日補充確認：無 `_C`／`_M` 分型的 BWA／Fixed／Spring，全部視作 Contact 邊界；明確 `_M` 仍為 Messenger。v2 邊界審閱保留此決策的 provenance。此規則解決端點角色，不自動批准任意 TL 連續配對或 coverage 完整性。

## 發布入口

Runtime metadata workbook 旁的可選 JSON：例如 `ISL metadata.approved-intervals.json`。沒有 sidecar 時，正式 TL／Overlap／Landmark 維持空值，Bracket 證據仍可查看。sidecar 存在但 schema、來源 SHA 或批准資料失效時明確停止分析，不退回猜測值。

以下只是 schema 範例，**不是實際批准資料，不可直接放入 config**。

```json
{
  "schema_version": "approved-contact-intervals-v1",
  "chainage_unit": "m",
  "sources": {
    "metadata": {"path": "ISL metadata.xlsx", "sha256": "核准時的實際SHA256"},
    "engineering": {"path": "../approved-source/engineering.xlsx", "sha256": "核准來源的實際SHA256"}
  },
  "approvals": {
    "approval-reference": {
      "approved_by": "資料負責人",
      "approved_at": "2026-10-29",
      "scope": "明確記錄線路、分支、方向、Contact配對、連續範圍及涵蓋完整性"
    }
  },
  "contexts": [{
    "line": "ISL", "session": "Mainline", "direction": "UT",
    "tension_lengths": [{
      "from_m": 100, "to_m": 200, "closed": "both",
      "tension_length": "範例TL", "wire_role": "contact",
      "approval_id": "approval-reference", "source_ids": ["metadata", "engineering"]
    }],
    "landmarks": [],
    "coverage": [{
      "from_m": 100, "to_m": 200, "closed": "both", "complete_tl_set": false,
      "approval_id": "approval-reference", "source_ids": ["metadata", "engineering"]
    }]
  }]
}
```

`line/session/direction` 必須等於分析 API 正規化後的 context，不跨方向或分支借用。每個 interval／coverage 都必須有批准及非空來源引用；sources 必須包含當前 runtime workbook 的 SHA。所有座標均為公尺，v1 僅接受 closed=both 的實體來源區間。Landmark 記錄使用 `landmark` 欄代替 `tension_length/wire_role`，亦須核准實際範圍。

## 區間與未知狀態

- 端點掃描拆成閉合單點與兩端開放的 span；兩條 TL 只在端點相接時，Overlap Y 只出現在該點，不延伸到旁邊。
- 兩個或以上已核准 Contact TL 在位置同時有效時可回 Y；單一有效 TL 只有在該位置具 `complete_tl_set=true` 的批准 coverage 才回 N。缺端、未分型或未完整盤點不能批准完整性。
- 沒有 active TL 的位置維持空值，即使有 coverage 也不自動推 N。
- 多個不同 Landmark 範圍命中會回 ambiguous，不任選其中一個。
- capabilities 的 available/partial 代表來源能力；`metadata_enrichment` 記錄峰值位置的 matched／no_approved_interval／outside_coverage／unresolved_pairing／ambiguous，不能把整張表的能力視為每個位置均完整。

## 既有行為與匯出

可選 enrichment 在 median reduction 後填入，避免新增 reduction segment 或改變例外 ID。Detector 原有 first-nonempty enrichment 保留；報表值可能取自例外範圍內另一位置，峰值診斷另列，不覆蓋正式值。

API 及「依據」視窗顯示峰值狀態；Excel 的 `MetadataEvidence` 記錄相同 JSON，`MetadataBoundaryReview` 逐列保存觀察及來源證據。大型 review 不塞入單一 `_Metadata` 儲存格，以免超過 Excel 32767 字元限制。隱藏 `_Metadata` 保留能力、版本與 digest；Summary 及各例外工作表欄位順序不變。

Wear lookup 仍要求另外核准的計算範圍／策略，本次不因 Exception Report 有 Contact 區間而解除既有 wear gate。

## 資料啟用

目前沒有建立任何 runtime sidecar。最新候選位於 `outputs/metadata-review-2026-10-29/batch-04`（batch-02 為無分型角色確認前的歷史證據），原始 workbook、release manifest 與 runtime config 均未覆寫。取得具體區間／完整性批准後，才可做來源備份、scope 與 SHA 核對、建立 sidecar、回歸及 release 更新；設計批准或 validator 通過均不等於資料啟用批准。使用者確認64格 runtime 差異是有意調整並指示保留現值；本次不因此改寫 release manifest。
