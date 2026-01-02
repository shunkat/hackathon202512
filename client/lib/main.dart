import 'dart:async';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '定期撮影デモ',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.indigo),
      ),
      home: const MyHomePage(title: '定期撮影デモ'),
    );
  }
}

class MyHomePage extends StatefulWidget {
  const MyHomePage({super.key, required this.title});

  final String title;

  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> with WidgetsBindingObserver {
  CameraController? _controller;
  Timer? _shotTimer;
  PermissionStatus? _permissionStatus;
  bool _isInitializing = true;
  bool _isSending = false;
  DateTime? _lastSentAt;
  int? _lastPayloadSize;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _initFlow();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _shotTimer?.cancel();
    _controller?.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && _controller != null) {
      _startTimer();
    }
    if (state == AppLifecycleState.inactive || state == AppLifecycleState.paused) {
      _shotTimer?.cancel();
    }
  }

  Future<void> _initFlow() async {
    setState(() {
      _isInitializing = true;
      _errorMessage = null;
    });

    await _requestPermission();
    if (!_isPermissionGranted) {
      setState(() => _isInitializing = false);
      return;
    }
    await _initializeCamera();
    _startTimer();
    setState(() => _isInitializing = false);
  }

  Future<void> _requestPermission() async {
    final status = await Permission.camera.request();
    setState(() {
      _permissionStatus = status;
    });
  }

  bool get _isPermissionGranted => _permissionStatus?.isGranted ?? false;

  Future<void> _initializeCamera() async {
    try {
      await _controller?.dispose();
      final cameras = await availableCameras();
      if (cameras.isEmpty) {
        setState(() {
          _errorMessage = '利用可能なカメラが見つかりませんでした。';
        });
        return;
      }
      final backCamera = cameras.firstWhere(
        (camera) => camera.lensDirection == CameraLensDirection.back,
        orElse: () => cameras.first,
      );
      final controller = CameraController(
        backCamera,
        ResolutionPreset.medium,
        enableAudio: false,
        imageFormatGroup: ImageFormatGroup.jpeg,
      );
      await controller.initialize();
      setState(() {
        _controller = controller;
      });
    } catch (e) {
      setState(() {
        _errorMessage = 'カメラ初期化に失敗しました: $e';
      });
    }
  }

  void _startTimer() {
    if (_controller == null || !_controller!.value.isInitialized) {
      return;
    }
    _shotTimer?.cancel();
    _shotTimer = Timer.periodic(
      const Duration(seconds: 10),
      (_) => _captureAndSend(),
    );
    _captureAndSend();
  }

  Future<void> _captureAndSend() async {
    final controller = _controller;
    if (controller == null || !controller.value.isInitialized || _isSending) {
      return;
    }
    setState(() {
      _isSending = true;
    });
    try {
      final file = await controller.takePicture();
      final bytes = await file.readAsBytes();

      // サーバー送信のモック。ここでHTTPクライアントに差し替えられる。
      await Future<void>.delayed(const Duration(milliseconds: 500));

      if (!mounted) return;
      setState(() {
        _lastSentAt = DateTime.now();
        _lastPayloadSize = bytes.length;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessage = '撮影または送信に失敗しました: $e';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isSending = false;
        });
      }
    }
  }

  Future<void> _openSettings() async {
    await openAppSettings();
  }

  @override
  Widget build(BuildContext context) {
    final controller = _controller;
    final permissionLabel = _permissionStatus == null
        ? '未確認'
        : _isPermissionGranted
            ? '許可済み'
            : _permissionStatus!.isPermanentlyDenied
                ? '永久に拒否（設定アプリから許可してください）'
                : '未許可';

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.title),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'カメラ権限: $permissionLabel',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 8),
              if (_isInitializing) ...[
                const Center(child: CircularProgressIndicator()),
              ] else if (!_isPermissionGranted) ...[
                Text(
                  'カメラへのアクセスが許可されていません。許可後に定期撮影を開始します。',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 12),
                ElevatedButton(
                  onPressed: _requestPermission,
                  child: const Text('権限を再度確認する'),
                ),
                if (_permissionStatus?.isPermanentlyDenied ?? false)
                  TextButton(
                    onPressed: _openSettings,
                    child: const Text('設定を開く'),
                  ),
              ] else ...[
                if (controller != null && controller.value.isInitialized)
                  AspectRatio(
                    aspectRatio: controller.value.aspectRatio,
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(12),
                      child: CameraPreview(controller),
                    ),
                  )
                else
                  const Center(child: Text('カメラの準備中です…')),
                const SizedBox(height: 12),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.autorenew, size: 18),
                            const SizedBox(width: 6),
                            Text(
                              '10秒ごとに自動撮影・モック送信します。',
                              style: Theme.of(context).textTheme.bodyMedium,
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text(
                          _lastSentAt == null
                              ? 'まだ送信していません'
                              : '直近送信: ${_lastSentAt!.toLocal()} (サイズ: ${_lastPayloadSize ?? 0} bytes)',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                        if (_isSending)
                          const Padding(
                            padding: EdgeInsets.only(top: 6),
                            child: Row(
                              children: [
                                SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                ),
                                SizedBox(width: 8),
                                Text('送信中…'),
                              ],
                            ),
                          ),
                      ],
                    ),
                  ),
                ),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _captureAndSend,
                        icon: const Icon(Icons.camera),
                        label: const Text('今すぐ撮影する'),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _initFlow,
                        icon: const Icon(Icons.refresh),
                        label: const Text('再初期化'),
                      ),
                    ),
                  ],
                ),
              ],
              if (_errorMessage != null) ...[
                const SizedBox(height: 12),
                Text(
                  _errorMessage!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
