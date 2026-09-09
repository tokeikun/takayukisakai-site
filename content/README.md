# 画面から編集する（おすすめ）

1. サイトフォルダの **「ポートフォリオを編集.command」** をダブルクリックします。
2. 左側からトップページ・ことば・プロフィール・作品を選びます。
3. 文章をクリックして書き換えます。下書きはこのMacへ自動保存されます。
4. **「プレビューに反映」** を押すと、元のサイトファイルが更新され、右側で見え方を確認できます。

- **作品を追加**：左側の「作品」の横にある「＋」。タイトルを書いて、表紙の写真を選びます。
- **画像・動画**：選択画面の「ファイルを追加」から。JPEG・PNG・WebP・GIF・MP4、32MBまで。
- **見出し・箇条書き**：文章の上に現れるメニューで切り替えます。太字やリンクは、ことばを選択してから。
- **ブロックの順番**：文章の上の ↑ / ↓。削除直後は「元に戻す」で戻せます。
- **作品の並び順**：左側の「作品の並び順」で、ドラッグか ↑ / ↓。★を付けた3作品までがトップに表示されます。
- **日本語・英語**：ページ上部のタブで切り替えます。
- **次回も続きから**：起動用ファイルをもう一度ダブルクリックします。保存済みの下書きが戻ります。

「下書き保存済み」はこのMacへの保存です。「プレビューに反映」も、公開中のサイトには反映しません。公開する場合は、確認した変更を既存の公開手順で送ります。

反映前の内容は `.editor/history/`、下書きは `.editor/draft.json` に保存されます。これらは公開先へ送られません。別の場所でも編集されていた場合は上書きを止め、下書きを保持します。

以前の `admin.html` は公開先を直接編集するための旧画面です。このMacでは新しい編集画面を使ってください。

---

# サイトの文章を自分で直す・作品を足す方法

このフォルダの中のテキストファイルが、サイトの「中身」です。
デザイン（template.html）とビルド（build.py）は触らなくてOK。

## 文章を直したいとき
1. 直したいファイルを開く（メモ帳・VSCode・なんでも）
   - サイト全体の文章（ヒーロー／エッセイ／略歴／連絡）→ `content/site.md`
   - 各作品 → `content/works/○○○_作品名.md`
2. 文章を書き換えて保存
3. ターミナルでプロジェクトフォルダに入り、次を実行：

```bash
python3 build.py
```

これで `index.html`、`works/`、固定ページ、`sitemap.xml` が新しい内容で再生成されます。
（Claudeに「ビルドして」と言うだけでもOK）

## 作品を新しく足したいとき
1. `content/works/` の中の既存ファイルをひとつ複製する
2. ファイル名の頭の数字が全作品一覧の表示順（小さいほど上）。トップの代表作は `featured: 1`、`featured: 2`、`featured: 3` で指定。トップに出さない作品は `featured` を省略する
3. 中身を書き換える：

```
id: new-work            ← 英数字とハイフンだけ。他とかぶらないように
title: 作品名
card: yes               ← yes=画像付きカード ／ row=文字だけの行
featured: 1             ← トップの代表作に出す場合のみ。番号の重複は避ける
year: 2026
year_detail: 2026 ・ 2 weeks
image: new-work.jpg     ← assets/ に入れた画像ファイル名
video: https://youtu.be/○○○   ← あれば。YouTube/Vimeo のURLをそのまま
video_file: demo.mp4    ← サイト内で再生するMP4（assets/ 内。あれば）
video_poster: cover.jpg ← 動画の表紙画像（省略時は image を使用）
gallery: a.jpg, b.jpg   ← 詳細ページの追加画像（あれば）

## desc.ja
一覧に出る短い説明（日本語）

## desc.en
Short description (English)

## fact.ja
技法 ／ 共作者 ／ 受賞など

## fact.en
Same in English

## concept.ja
カードに引用として出る、コンセプトの一文（なければ丸ごと省略OK）

## detail.ja
詳細ページの本文。

空行で段落を分ける。

## detail.en
Detail text in English.

## process.ja
### 制作の背景

何を試し、どう考えたか。詳細本文のあとに表示。

## process.en
### Behind the work

What was explored and how.

## video_caption.ja
動画の内容、試作の時期、音声の有無など。

## video_caption.en
Clip description, study date and sound information.
```

4. 画像を `assets/` フォルダに入れる
5. `python3 build.py`

## 消したいとき
ファイルを削除（またはファイル名の先頭に `_` を付けて退避）→ `python3 build.py`

## 注意
- ファイルは必ず **UTF-8** で保存（普通のエディタならそのまま）
- `## 見出し` の行は消さない・綴りを変えない
- 分からなくなったら Claude に「content/○○を直して」と頼めば代わりにやります

## 固定ページ（できること／プレス資料 など）
`content/pages/○○.md` が 1ページ = `/○○/` になります（例：`contact.md` → takayukisakai.com/contact/）。
- ヘッダ：`slug`（URL）、`title_ja` / `title_en`、`desc_ja` / `desc_en`、`draft`
- **`draft: yes` のあいだは noindex・フッター未リンク**（URLを知っている人だけ見られる確認用）。公開するときは `draft: no` に
- 本文は `## 名前.ja` / `## 名前.en` のペア。`### 見出し`、`- リスト`、`**太字**`、`[文字](URL)`、`![説明](画像URL)` が使えます
- `{{form}}` と書いた場所に、`content/site.md` の `contact_form:` のURLがフォームとして埋め込まれます
