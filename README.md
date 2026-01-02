# hackathon202512

モノレポ構成で server / client をまとめています。client は Flutter アプリ（カメラ側）、server は Firebase Functions を想定した PoC 用サーバー側です。

## ディレクトリ構成
- `server/` : サーバーコード（Firebase Functions を想定。内容は今後追加）
- `client/` : Flutter 製モバイルアプリ

## 開発環境のセットアップ
1. FVM が未導入の場合はインストール  
   - 例: `brew install fvm` または `dart pub global activate fvm`
2. Flutter SDK を FVM で取得  
   - レポジトリ直下で `fvm install 3.38.5`
3. client でバージョンを適用  
   - `cd client`  
   - `fvm use 3.38.5`
4. 動作確認  
   - `fvm flutter doctor`

以降の Flutter コマンドは `client` ディレクトリで `fvm flutter ...` と実行してください。

## 開発の進め方
- クライアント側: `client/README.md` を参照（FVM での実行方法や主要コマンドを記載）。
- サーバー側: `server/` 配下に追記予定。
