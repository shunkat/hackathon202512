import Flutter
import UIKit
import AVFoundation

@main
@objc class AppDelegate: FlutterAppDelegate {
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    GeneratedPluginRegistrant.register(with: self)

    // カメラのシャッター音を無音にするためのオーディオセッション設定
    setupAudioSession()

    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  private func setupAudioSession() {
    do {
      // オーディオセッションを ambient に設定してシステムサウンドを抑制
      try AVAudioSession.sharedInstance().setCategory(.ambient)
      try AVAudioSession.sharedInstance().setActive(true, options: [])
    } catch {
      print("Failed to set audio session: \(error)")
    }
  }

  override func applicationDidBecomeActive(_ application: UIApplication) {
    super.applicationDidBecomeActive(application)
    // アプリがアクティブになったときにも設定を適用
    setupAudioSession()
  }
}
