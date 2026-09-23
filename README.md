# 星の鳥
## Comet Orbit Database for Nicole — GitHub Static DB v2

星の鳥は、JPL Small-Body Database (SBDB) の彗星データを定期的に取得し、
GitHub Pages から静的 JSON として配信する Nicole 用データセットです。

## 構成

```text
Hoshinotori/
├── index.html
├── data/
│   ├── meta.json
│   ├── catalog/
│   │   ├── index.json
│   │   ├── 00.json
│   │   ├── 01.json
│   │   └── ... 3f.json
│   └── comets/
│       └── <bucket>/<spkid>.json
├── scripts/
│   ├── common.py
│   ├── update_catalog.py
│   ├── fetch_detail.py
│   └── refresh_existing_details.py
└── .github/
    └── workflows/
        ├── update-comets.yml
        └── fetch-comet-detail.yml
```

### data/catalog/index.json
Nicole の検索用の軽量インデックスです。
全彗星の名前・designation・SPK-ID・orbit_id・epoch・軌道分類などを持ちます。

### data/catalog/00.json ～ 3f.json
基本軌道要素を 64 シャードに分割して保存します。
SPK-ID を 64 で割った余りを16進2桁にしたものが bucket です。

### data/comets/<bucket>/<spkid>.json
必要な彗星だけ詳細データを保存します。
共分散、軌道要素の不確かさ、非重力モデルパラメータ、物理パラメータ、
alternate designation などを含められます。

詳細 JSON は最初から全彗星分を作る必要はありません。

## 更新方針

### 自動更新
`.github/workflows/update-comets.yml`

1日1回 JPL SBDB Query API を確認します。

- 全彗星の基本カタログを取得
- 既存 JSON と比較
- 内容が変わったファイルだけ Git に書き込む
- 既に詳細 JSON が存在する彗星について、orbit_id / epoch が変化した場合だけ詳細を再取得
- 変更がなければ commit しない

### 詳細データを追加する
GitHub の Actions 画面から `Fetch one comet detail` を手動実行し、
SPK-ID を入力します。

これにより、その彗星だけ

`data/comets/<bucket>/<spkid>.json`

へ保存されます。

## Nicole 側の利用想定

### 検索
```js
const index = await fetch(
  "https://<USER>.github.io/<REPO>/data/catalog/index.json"
).then(r => r.json());
```

### 簡易計算
検索結果の `bucket` を使って基本軌道シャードを取得します。

```js
const shard = await fetch(
  `https://<USER>.github.io/<REPO>/data/catalog/${bucket}.json`
).then(r => r.json());
```

### 精密計算
詳細 JSON が存在する彗星なら、

```text
data/comets/<bucket>/<spkid>.json
```

を追加取得します。

詳細ファイルがまだ無い場合は、将来の Nicole では
「JPLからライブ取得（Cloudflare Worker経由）」へフォールバックできます。
Worker は D1 への保存を行わず、JPL との中継専用にできます。

### JPL高精度
観測者位置からの見かけの RA/Dec は静的軌道要素だけではなく、
JPL Horizons のライブ問い合わせを使う設計を推奨します。

## GitHub Pages

リポジトリ作成後、

`Settings → Pages → Deploy from a branch`

で、

- Branch: `main`
- Folder: `/ (root)`

を選択します。

## 初回セットアップ

1. 新しい GitHub リポジトリを作成（例: `Hoshinotori`）
2. このフォルダの中身をリポジトリ直下へアップロード
3. Actions を有効化
4. `Update comet catalog` を一度手動実行
5. Pages を有効化
6. `index.html` で状態を確認
7. Nicole の星の鳥 URL を GitHub Pages 側へ変更

## 注意

- JPL SBDB Query API はページング中に基礎データが更新される可能性があります。
  本スクリプトは `spkid` 順で一巡して取得します。
- GitHub Pages は静的配信です。ブラウザから安全に GitHub のファイルを直接更新することはしません。
- GitHub Actions の scheduled workflow は default branch 上で実行されます。
- 公開リポジトリで長期間活動がない場合、scheduled workflow が停止する場合があります。
