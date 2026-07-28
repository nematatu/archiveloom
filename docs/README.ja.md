<p align="center">
  <img src="assets/brand/logo.svg" width="520" alt="ArchiveLoom ロゴ">
</p>

<p align="center"><strong>Web上のメディアを、信頼できるローカルアーカイブへ。</strong></p>

<p align="center">
  <a href="https://github.com/nematatu/archiveloom#readme">English</a> ·
  <a href="installation.md">インストール</a> ·
  <a href="usage.md">使い方</a> ·
  <a href="AGENT_PROMPT.ja.md">AI実装プロンプト</a> ·
  <a href="case-study-inhigh-tv.ja.md">InHigh TV実例</a> ·
  <a href="adapters.md">アダプター開発</a> ·
  <a href="https://github.com/nematatu/archiveloom/blob/main/CONTRIBUTING.md">コントリビュート</a>
</p>

**ArchiveLoomは、InHigh TV専用の一括ダウンローダーで培った核の部分を抽出・一般化し、macOS・Windows・Linuxで再利用できるソフトウェアとしてOSS化したものです。**

動画の複数選択、一括並列ダウンロード、中断・再開、固定進捗表示、外付けHDD限定保存、FFmpeg処理、完成ファイル検証などを共通のコアとして提供します。数十本の長時間映像や、就寝中の長時間実行など、ブラウザーのダウンロードボタンだけでは扱いにくい場面が対象です。

## ArchiveLoomとは何か・何ではないか

ArchiveLoomが目指しているのは、**対応している動画配信サイトのページURLを渡し、発見された動画を確認・選択して、そのまま一括保存できる体験**です。

ただし、サイトごとに一覧ページ、日付、カテゴリー、ページ送り、プレイヤー、動画URLの取得方法が異なります。そのため、現時点のArchiveLoomは「あらゆるページURLを自動解析する万能ダウンローダー」ではなく、安定したダウンロードコアと、追加可能なサイト専用アダプターを組み合わせる設計です。

目的は、サイトが変わるたびに一括ダウンロード部分を作り直さず、サイト構造を理解する小さなアダプターだけを追加すればよい状態にすることです。

| ArchiveLoomへ渡すもの | そのまま利用できるか |
|---|---|
| 動画ファイル、HLS（`.m3u8`）、DASH（`.mpd`）の直接URL | **できます** |
| 既知の動画URLを記載したArchiveLoom JSONコレクション | **できます** |
| 独自プレイヤーや動画一覧を含む通常のWebページURL | **対応アダプターが必要です** |
| DRM保護された映像やアクセス制御の回避 | **できません。意図的に対応しません** |

対応アダプターが存在しないサイトでは、最初に開発者またはAIコーディングエージェントが、利用を許可された公開インターフェースを調査して発見処理を実装する必要があります。ArchiveLoomをインストールしただけで、任意のWebページURLを保存できるようになるわけではありません。実装手順は[AI・実装者向け設計ブループリント](engineering-blueprint.ja.md)にまとめています。

## このOSSの中心となる使い方

未対応サイトでは、ArchiveLoomを最初から作り直すのではなく、対象URLとこのリポジトリをAIコーディングエージェントへ渡します。

```text
ArchiveLoomリポジトリを開き、docs/AGENT_PROMPT.ja.mdを最初から最後まで読んでください。

対象サイトURL: https://example.com/archive
保存が許可されている対象: <対象範囲を書く>
選択したい分類: <日付、カテゴリー、会場、カメラなど>
ファイル名形式: <希望形式>
実行してよい範囲: アダプターの実装とテストまで。全件ダウンロードは開始しない

プロンプトに記載された調査、安全確認、テスト、引き渡し要件に従ってください。
```

実際の流れは次のとおりです。

1. AIが[`docs/AGENT_PROMPT.ja.md`](AGENT_PROMPT.ja.md)と、そこから指定された設計書を読みます。
2. AIが対象サイトを実測調査し、ページ構造や動画URLの解決方法を確認します。
3. AIがそのサイト専用のアダプターとテストを作ります。
4. AIがインストール方法、一覧確認、書き込みなし確認、実行コマンドを提示します。
5. ユーザーが取得一覧を確認し、自分でダウンロードを開始します。

これが、現時点で「未知のサイトページURL」から「ArchiveLoomで一括保存」へつなぐ基本ワークフローです。将来的には公式・コミュニティ製アダプターを増やし、対応サイトならURLを渡すだけで使える範囲を広げます。

AIを使っても、すべてのサイトへ必ず対応できるとは限りません。DRM、許可されていないアクセス、安定して利用できない認証、公開インターフェースが存在しない場合は、回避せず理由を示して停止することをプロンプトで要求しています。

## 現在すぐ使えるケース

### 1. HLSなど、実際の動画URLが分かっている

サイトページのURLではなく、`master.m3u8`などの実際の動画URLが分かっている場合は、そのまま確認・保存できます。最初に`--check-only`で書き込みをせず確認します。

```console
archiveloom --lang ja download \
  "https://example.com/video/master.m3u8" \
  --output "/Volumes/ExternalHDD/archive" \
  --check-only
```

確認後、`--check-only`を外すと保存を開始します。

```console
archiveloom --lang ja download \
  "https://example.com/video/master.m3u8" \
  --output "/Volumes/ExternalHDD/archive"
```

### 2. 分かっている複数の動画URLから選んで保存する

動画一覧を`collection.json`へ記載します。

```json
{
  "version": 1,
  "items": [
    {
      "id": "2026-07-23-court-01",
      "title": "7月23日 コート1",
      "url": "https://example.com/court01/master.m3u8",
      "protocol": "hls",
      "filename": "2026-07-23_01.mp4"
    },
    {
      "id": "2026-07-23-court-02",
      "title": "7月23日 コート2",
      "url": "https://example.com/court02/master.m3u8",
      "protocol": "hls",
      "filename": "2026-07-23_02.mp4"
    }
  ]
}
```

対話形式で動画を選択し、2本ずつ並列処理する例です。

```console
archiveloom --lang ja download collection.json \
  --output "/Volumes/ExternalHDD/archive" \
  --interactive \
  --jobs 2
```

```text
ArchiveLoom

[x] 2026-07-23 コート01
[x] 2026-07-23 コート02
[ ] 2026-07-24 コート01
[x] 2026-07-24 コート02

j/k・↑/↓  移動       Space  選択・解除
a          全選択     Enter  決定
q          終了
```

## 一般的なサイトのページに対応させる場合

`https://example.com/event`のような通常のWebページを渡すだけでは、そのサイトの動画一覧を取得できません。日付、会場、カテゴリー、ページ送り、プレイヤー情報、メディアIDなどを理解するサイト専用アダプターが必要です。

アダプターのひな型は生成できます。

```console
archiveloom adapters scaffold example_site --output ./plugins
```

例えば、AIコーディングエージェントには[専用の日本語プロンプト](AGENT_PROMPT.ja.md)を読み込ませたうえで、次のように依頼します。

> このサイトのアーカイブ動画をArchiveLoomで保存できるようにしてください。
> 日付と会場で選択できるサイト専用アダプターを作ってください。
> `docs/engineering-blueprint.ja.md`の設計、安全要件、テスト要件に従ってください。

AIまたは開発者がサイトを調査し、専用アダプターを実装・テストします。完成したアダプターをインストールすると、サイトのページ構造がArchiveLoom共通の動画一覧へ変換され、同じ選択画面とダウンロード処理を利用できる設計です。

## InHigh TVとの関係

InHigh TVは、ArchiveLoomの考え方を説明するための架空の例ではありません。公開リポジトリ[`inhigh-tv-tools`](https://github.com/nematatu/inhigh-tv-tools)には、2026年バドミントン映像を対象とした実用済みの専用ダウンローダーがあります。

| ツール | 現在の状態 |
|---|---|
| InHigh TV専用`.command` | 実際のサイト構造に対応し、日付・コート選択、並列保存、外付けHDD限定、進捗、中断、再試行、完成検証を実装済みです |
| ArchiveLoom | 多様なサイトへ展開するための汎用OSS基盤。InHigh TV専用アダプターはまだ同梱していません |

ArchiveLoomは、その専用実装からサイトに依存しない核を抽出・一般化したものです。現時点では、InHigh TVのサイト解析部分は専用`.command`側に残っているため、ページURLをArchiveLoomへ渡すだけではアーカイブ一覧を取得できません。

実装済み機能、サイト固有部分と共通コアの対応、実際の件数、移植をAIへ依頼する完成済みプロンプトは、[InHigh TVケーススタディ](case-study-inhigh-tv.ja.md)で確認できます。

<p align="center">
  <img src="assets/screenshots/dashboard.svg" width="900" alt="ArchiveLoomの固定進捗画面">
</p>

> [!IMPORTANT]
> 現在はアルファ版です。安全設計とプラグインAPIは利用できますが、最初の安定版と署名済み単体バイナリは今後の予定です。

## 特長

- **大量取得を前提** — 発見、確認、複数選択、保存、検証を1回の実行で管理します。
- **サイト別アダプター** — サイト固有処理をコアから分離します。
- **安全な保存** — 黙って上書きせず、外付け限定時は内部ディスクへ退避しません。
- **再実行可能** — 完了済み正常ファイルを除外し、直接HTTPはRange再開を試みます。
- **固定進捗画面** — 端末を同じ進捗行で埋めません。
- **完成検証** — `ffprobe`合格後だけ最終ファイル名へ確定します。
- **クロスプラットフォーム** — macOS、Windows、LinuxをCI対象にします。
- **多言語基盤** — 英語・日本語の主要メッセージとドキュメントを提供します。

## クイックスタート

### 1. FFmpegをインストール

HLS/DASH処理と完成検証に`ffmpeg`・`ffprobe`を使います。OS別の手順は[インストールガイド](installation.md)を参照してください。

### 2. GitHubからインストール

```console
pipx install git+https://github.com/nematatu/archiveloom.git
```

または:

```console
uv tool install git+https://github.com/nematatu/archiveloom.git
```

### 3. PCと保存先を診断

```console
archiveloom --lang ja doctor --output /保存先
```

物理的な外付け保存先だけを許可する場合:

```console
archiveloom --lang ja doctor --output /保存先 --external-only
```

### 4. 書き込みなしで確認

```console
archiveloom --lang ja download collection.json \
  --output /保存先 \
  --check-only
```

### 5. 複数選択して開始

```console
archiveloom --lang ja download collection.json \
  --output /保存先 \
  --interactive \
  --jobs 2
```

`↑/↓`または`j/k`で移動、`Space`で選択、`a`で全選択、`Enter`で決定します。

## バドミントンやスポーツ専用ではありません

サイト固有の分類はアダプターが`dimensions`として渡します。

- スポーツ: 日付、大会、会場、コート
- カンファレンス: 日、トラック、セッション
- 講義: 科目、回、講師
- カメラ: 拠点、カメラ、時間帯

コアエンジンには「日付」「コート」などを固定実装しません。

## 対応入力

- 直接HTTP(S)メディアURL
- HLS `.m3u8`
- MPEG-DASH `.mpd`
- ArchiveLoom JSONコレクション
- インストール済みの外部サイトアダプター

DRM、アクセス制御、課金、認証を回避しません。詳しくは[責任ある利用](responsible-use.md)を参照してください。

## アダプターの作成

```console
archiveloom adapters scaffold my_site --output ./plugins
```

アダプターは通常のPythonパッケージとして配布できます。詳細は[アダプター開発ガイド](adapters.md)を参照してください。

## ドキュメント

- [インストール](installation.md)
- [使い方・終了コード](usage.md)
- [アーキテクチャ](architecture.md)
- [AIサイトアダプター実装プロンプト](AGENT_PROMPT.ja.md)
- [InHigh TV実例ケーススタディ](case-study-inhigh-tv.ja.md)
- [AI・実装者向け設計ブループリント](engineering-blueprint.ja.md)
- [アダプター開発](adapters.md)
- [責任ある利用](responsible-use.md)
- [セキュリティポリシー](https://github.com/nematatu/archiveloom/blob/main/SECURITY.md)
- [ロードマップ](https://github.com/nematatu/archiveloom/blob/main/ROADMAP.md)

## コントリビュート

不具合報告、アダプター提案、翻訳、Windows/Linux実機テスト、ドキュメント改善を歓迎します。[CONTRIBUTING.md](https://github.com/nematatu/archiveloom/blob/main/CONTRIBUTING.md)と[行動規範](https://github.com/nematatu/archiveloom/blob/main/CODE_OF_CONDUCT.md)を確認してください。

## ライセンス

[MIT License](https://github.com/nematatu/archiveloom/blob/main/LICENSE)です。各サイトアダプターやリリースへ同梱する依存物には、別のライセンスが適用される場合があります。
