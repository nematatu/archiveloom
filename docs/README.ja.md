<p align="center">
  <img src="assets/brand/logo.svg" width="520" alt="ArchiveLoom ロゴ">
</p>

<p align="center"><strong>Web上のメディアを、信頼できるローカルアーカイブへ。</strong></p>

<p align="center">
  <a href="https://github.com/nematatu/archiveloom#readme">English</a> ·
  <a href="installation.md">インストール</a> ·
  <a href="usage.md">使い方</a> ·
  <a href="adapters.md">アダプター開発</a> ·
  <a href="https://github.com/nematatu/archiveloom/blob/main/CONTRIBUTING.md">コントリビュート</a>
</p>

ArchiveLoomは、自分が所有している、または保存を許可されているメディアの**コレクション**を安全に保存するための、macOS・Windows・Linux対応CLI/TUIです。

数十本の長時間映像、複数日・複数会場、外付けHDD限定保存、就寝中の長時間実行など、ブラウザーのダウンロードボタンだけでは扱いにくい場面を対象にしています。

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
- [AI・実装者向け設計ブループリント](engineering-blueprint.ja.md)
- [アダプター開発](adapters.md)
- [責任ある利用](responsible-use.md)
- [セキュリティポリシー](https://github.com/nematatu/archiveloom/blob/main/SECURITY.md)
- [ロードマップ](https://github.com/nematatu/archiveloom/blob/main/ROADMAP.md)

## コントリビュート

不具合報告、アダプター提案、翻訳、Windows/Linux実機テスト、ドキュメント改善を歓迎します。[CONTRIBUTING.md](https://github.com/nematatu/archiveloom/blob/main/CONTRIBUTING.md)と[行動規範](https://github.com/nematatu/archiveloom/blob/main/CODE_OF_CONDUCT.md)を確認してください。

## ライセンス

[MIT License](https://github.com/nematatu/archiveloom/blob/main/LICENSE)です。各サイトアダプターやリリースへ同梱する依存物には、別のライセンスが適用される場合があります。
