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

## Firebase セットアップ（Cloud Storage + Firestore）
1. Firebase プロジェクト作成後、Cloud Storage と Firestore を「テストモード」または適切なルールで有効化してください。
2. アプリ登録  
   - Android: Firebase コンソールで Android アプリを登録し、`android/app/google-services.json` を配置。必要に応じて `android/app/build.gradle.kts` の `applicationId` を Firebase に登録したパッケージ名へ変更。  
   - iOS: iOS アプリを登録し、`ios/Runner/GoogleService-Info.plist` を追加（Runner.xcodeproj にドラッグ＆ドロップ）。  
   - macOS でも動かす場合は macOS アプリ登録を行い、`macos/Runner/GoogleService-Info.plist` を配置。
3. Android は `android/settings.gradle.kts` で Google Services プラグインを読み込む設定済みなので、`google-services.json` 配置後に `fvm flutter pub get` → `fvm flutter run` で初期化されます。iOS/macOS は `fvm flutter pub get` 後に `cd ios && pod install`（macOS は `cd macos && pod install`）を実行してください。
4. FlutterFire CLI で自動設定したい場合は `dart pub global activate flutterfire_cli` の後、`fvm flutterfire configure --platforms=android,ios,macos` を実行すると各プラットフォームへ設定ファイルが配置されます（`firebase_options.dart` を出力する場合は `--out=lib/firebase_options.dart` を付与）。

### ビルド時間短縮（iOS/macOS）
- Firestore を prebuilt 版で取り込むため、`ios/Podfile` と `macos/Podfile` で `pod 'FirebaseFirestore', :git => 'https://github.com/invertase/firestore-ios-sdk-frameworks.git'` を指定し、FlutterFire の `firebase_core` が持つ `firebase_sdk_version.rb` から SDK バージョン（例: 11.15.0）を自動で tag に反映しています。これにより Firestore のソースビルドを避け、Pod の取得とビルド時間を短縮します。
- `firebase_core` のバージョンを上げた場合は、`fvm flutter pub get` の後に再度 `pod install` を実行するだけで新しい SDK バージョンの prebuilt が使われます。もしバージョン取得が失敗した場合は、Podfile にフォールバック値（11.15.0）が使われるので、必要に応じて更新してください。

### 動作確認
- 設定ファイル配置後に `fvm flutter run` を実行し、撮影→Cloud Storage へアップロード→Firestore へパス保存までエラーが出ないことを確認してください。`lib/main.dart` のカード下部に保存先パスとダウンロード URL が表示されます。
