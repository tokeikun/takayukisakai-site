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

これで `real.html` が新しい内容で再生成されます。
（Claudeに「ビルドして」と言うだけでもOK）

## 作品を新しく足したいとき
1. `content/works/` の中の既存ファイルをひとつ複製する
2. ファイル名の頭の数字が表示順（小さいほど上）。例：`015_new-work.md` は umbrella-dance と kage の間に入る
3. 中身を書き換える：

```
id: new-work            ← 英数字とハイフンだけ。他とかぶらないように
title: 作品名
card: yes               ← yes=画像付きカード ／ row=文字だけの行
year: 2026
year_detail: 2026 ・ 2 weeks
image: new-work.jpg     ← assets/ に入れた画像ファイル名
video: https://youtu.be/○○○   ← あれば。YouTube/Vimeo のURLをそのまま
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
```

4. 画像を `assets/` フォルダに入れる
5. `python3 build.py`

## 消したいとき
ファイルを削除（またはファイル名の先頭に `_` を付けて退避）→ `python3 build.py`

## 注意
- ファイルは必ず **UTF-8** で保存（普通のエディタならそのまま）
- `## 見出し` の行は消さない・綴りを変えない
- 分からなくなったら Claude に「content/○○を直して」と頼めば代わりにやります
