# client

Flutter 製のモバイルアプリです。FVM 経由で Flutter 3.38.5 を使用します。

## 開発環境のセットアップ
1. レポジトリ直下で Flutter SDK を取得  
   `fvm install 3.38.5`
2. 本ディレクトリでバージョンを設定  
   `fvm use 3.38.5`
3. 依存関係の取得  
   `fvm flutter pub get`
4. 動作確認  
   `fvm flutter doctor`

以降、Flutter 関連のコマンドは必ず `fvm flutter ...` で実行してください。

## よく使うコマンド
- アプリ起動: `fvm flutter run -d <デバイスID>`
- テスト: `fvm flutter test`
- パッケージ取得: `fvm flutter pub get`
