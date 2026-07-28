# 実例: InHigh TV一括ダウンローダーからArchiveLoomへ

InHigh TVは、ArchiveLoomの仕組みを説明するために作った架空の例ではありません。ArchiveLoomは、実際に長時間・多数の大会映像を保存するために作成した専用ダウンローダーから、再利用可能な核を抽出・一般化して生まれました。

参照実装は、公開リポジトリ`nematatu/inhigh-tv-tools`の[`downloader/download_inhigh_2026.command`](https://github.com/nematatu/inhigh-tv-tools/blob/codex/interactive-download-cli/downloader/download_inhigh_2026.command)です。本ページの事実は、2026年7月28日にローカルと公開ブランチの同一性を確認したコードを読み取った内容です。サイト側の掲載状態は後から変化する可能性があります。

## 実際に解決した課題

対象は、2026年インターハイ・バドミントンの長時間アーカイブです。専用実装が検証用の期待値として保持している内訳は次のとおりです。

| 日付 | アーカイブ数 |
|---|---:|
| 2026-07-23 | 36本 |
| 2026-07-24 | 16本 |
| 2026-07-25 | 36本 |
| 2026-07-26 | 36本 |
| 2026-07-27 | 8本 |
| 合計 | 132本 |

1本が数時間に及ぶため、ブラウザーから手作業で順番に保存する運用では、対象選択、完了確認、中断、再実行、保存容量、進捗把握が問題になります。

## 専用ダウンローダーで実装済みの機能

読み取り確認できた専用`.command`の機能です。

- 日付を1日または複数日選択
- コート番号を1つまたは複数選択
- `j` / `k`、上下矢印、`Space`、`a`、`Enter`による対話選択
- 既定2本、指定可能範囲1〜36本の並列ダウンロード
- 最高画質を選択し、最大1080pへ制限可能
- 日付とコートから`2026-07-23_01.mp4`形式で命名
- 外付け物理HDDであることをmacOSの`diskutil`で検証
- 内蔵ストレージへのフォールバックを拒否
- 一時MP4、状態ファイル、ログも外付けHDD内へ配置
- 既存MP4を`ffprobe`で検証し、完成済みを選択肢から除外
- 動画時間、処理速度、残り時間、完了予定を固定領域へ表示
- HLS処理が180秒進まない場合に停滞として検出
- 失敗した項目を1回自動再試行し、キューの残りを継続
- `Ctrl+C`をFFmpegへ重複送信せず、MP4確定を待って段階的に停止
- 実行前に取得可能件数、合計時間、推定容量、HDD空き容量を確認
- `--check-only`では書き込みを開始せず調査結果だけを表示

これは構想ではなく、実際の長時間ダウンロードで利用されている専用実装です。

## 実際の専用ツールを確認する

現在の参照実装は公開ブランチで確認できます。次の例はmacOS向け専用ツールのため、ArchiveLoom本体のクロスプラットフォーム手順とは異なります。

```console
git clone https://github.com/nematatu/inhigh-tv-tools.git
cd inhigh-tv-tools
git switch codex/interactive-download-cli
cd downloader
./download_inhigh_2026.command --interactive --check-only
```

`--check-only`では動画保存を開始せず、実装は次の順に情報を提示します。

```text
サイトから対象一覧を確認
  ↓
日付ごとの掲載本数を表示
  ↓
外付け物理HDDと空き容量を検証
  ↓
完成済みMP4をffprobeで確認して候補から除外
  ↓
日付とコートをキーボードで複数選択
  ↓
HLS、画質、合計時間、推定容量を事前確認
  ↓
「確認のみで終了しました。ファイルは作成していません」
```

確認後、`--check-only`を外して再実行し、最終確認で`START`と入力した場合だけ本番保存を開始します。

## InHigh TV固有の処理

専用実装は、サイトを実測した結果に基づき、次の処理を行います。

1. InHigh TVのアーカイブ一覧APIをページ末尾まで取得します。
2. 大会IDと対象日付でバドミントンの記録を限定します。
3. タイトルからコート番号を抽出します。
4. 各記録のメディアIDを検証します。
5. 公開されているプレイヤー設定と再生情報からHLSを解決します。
6. HLSマスタープレイリストから、指定上限以下で最も高い画質を選択します。
7. VODプレイリストの再生時間とビットレートから時間・容量を見積もります。

この部分はInHigh TVのAPI、項目名、ID、プレイヤーに依存します。別サイトでは使い回せないため、ArchiveLoomではサイトアダプターの責任範囲になります。

## ArchiveLoomへ抽出した核

| InHigh TV専用実装で必要になったもの | ArchiveLoomでの担当 |
|---|---|
| 日付・コート・動画一覧の取得 | InHigh TVアダプター |
| ページ情報からHLS URLを解決 | InHigh TVアダプター |
| 日付・コートを選べる一覧 | 共通TUI＋アダプターの`dimensions` |
| 複数動画の並列実行 | 共通ダウンロードエンジン |
| 進捗、残り時間、終了予定 | 共通進捗エンジン |
| FFmpegによるHLS→MP4保存 | 共通プロトコル処理 |
| 完成済みの検出と再実行 | 共通状態・検証処理 |
| 外付けHDD確認 | OS別の共通ストレージ検査 |
| 中断、再試行、失敗後の継続 | 共通実行制御 |
| 安全なファイル名と完成検証 | 共通パス・`ffprobe`検証 |

ArchiveLoomの目的は、右列を新しいサイトごとに再実装しないことです。新規サイトでは左列上部の「一覧発見と動画URL解決」だけをアダプターとして追加します。

## 現在の状態

| 項目 | 状態 |
|---|---|
| InHigh TV専用ダウンローダー | 実装済み。専用リポジトリで利用可能 |
| ArchiveLoom共通コア | 実装済み。直接URLとJSONコレクションに対応 |
| ArchiveLoom用InHigh TVアダプター | 未移植・未同梱 |
| InHigh TVページURLをArchiveLoomへ直接渡す | 現時点では未対応 |

この区別が重要です。専用ダウンローダーが存在することと、ArchiveLoomへプラグインとして搭載済みであることは同じではありません。

## AIへ移植を依頼する具体例

ArchiveLoomと`inhigh-tv-tools`の両方をAIコーディングエージェントが参照できる状態で、次の依頼を渡します。

```text
ArchiveLoomのdocs/AGENT_PROMPT.ja.mdを最初から最後まで読んでください。

対象サイトURL:
https://inhightv.sportsbull.jp/summer/competition/9

参照実装:
https://github.com/nematatu/inhigh-tv-tools/blob/codex/interactive-download-cli/downloader/download_inhigh_2026.command

目的:
既存の専用スクリプトからInHigh TV固有の一覧取得、コート番号抽出、
メディア情報解決、HLS解決だけをArchiveLoomアダプターへ移植してください。
選択、並列実行、進捗、外付けHDD確認、FFmpeg、状態、検証は
ArchiveLoomの共通コアを使用してください。

対象分類:
日付、コート

ファイル名:
YYYY-MM-DD_CC.mp4

許可する作業:
調査、実装、匿名化fixtureによるテスト、inspect、check-onlyまで。
既存の.commandを変更・停止しないでください。
全件ダウンロードは開始しないでください。

専用実装を推測で写すのではなく、現在の公開サイト構造を再確認し、
検証済み事項と未検証事項を分けて報告してください。
```

AIは参照実装から既知の解決経路を学べますが、サイト構造が変わっている可能性があるため、現在のサイトを再確認する必要があります。

## 移植後に目指す操作

以下はInHigh TVアダプター移植後の目標例であり、現在のv0.1.0で実行できるコマンドではありません。

```console
archiveloom --lang ja inspect \
  "https://inhightv.sportsbull.jp/summer/competition/9"

archiveloom --lang ja download \
  "https://inhightv.sportsbull.jp/summer/competition/9" \
  --output "/Volumes/ExternalHDD/inhigh-tv-archive" \
  --external-only \
  --interactive \
  --jobs 2 \
  --check-only
```

一覧と保存先を確認した後、利用者が`--check-only`を外して本番を開始する設計です。

## この実例が示すこと

InHigh TV専用実装によって、ArchiveLoomが解決すべき共通問題は机上ではなく実運用から得られました。一方、サイト固有の発見処理まで万能化しないことで、別サイトの変更が共通ダウンロードエンジンを壊さない構造にしています。
