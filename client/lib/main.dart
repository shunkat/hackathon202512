import 'dart:async';
import 'dart:io';
import 'dart:math';

import 'package:camera/camera.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_storage/firebase_storage.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:permission_handler/permission_handler.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
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
  String? _userId;
  bool _isSigningIn = false;
  bool _isInitializing = true;
  bool _isSending = false;
  DateTime? _lastSentAt;
  int? _lastPayloadSize;
  String? _lastStoragePath;
  String? _lastDownloadUrl;
  String? _errorMessage;
  final _random = Random();

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
    if (state == AppLifecycleState.inactive ||
        state == AppLifecycleState.paused) {
      _shotTimer?.cancel();
    }
  }

  Future<void> _initFlow() async {
    setState(() {
      _isInitializing = true;
      _errorMessage = null;
    });

    await _ensureSignedIn();
    if (_userId == null) {
      setState(() => _isInitializing = false);
      return;
    }

    await _requestPermission();
    if (!_isPermissionGranted) {
      setState(() => _isInitializing = false);
      return;
    }
    await _initializeCamera();
    _startTimer();
    setState(() => _isInitializing = false);
  }

  Future<void> _ensureSignedIn() async {
    final auth = FirebaseAuth.instance;
    final currentUser = auth.currentUser;
    if (currentUser != null) {
      setState(() {
        _userId = currentUser.uid;
      });
      return;
    }

    setState(() {
      _isSigningIn = true;
    });
    try {
      final credential = await auth.signInAnonymously();
      if (!mounted) return;
      final uid = credential.user?.uid;
      setState(() {
        _userId = uid;
        _errorMessage =
            uid == null ? '匿名認証のユーザーIDを取得できませんでした。' : _errorMessage;
      });
    } on FirebaseAuthException catch (e, st) {
      debugPrint(
        'Anonymous sign-in failed: code=${e.code}, message=${e.message}',
      );
      debugPrintStack(stackTrace: st);
      if (!mounted) return;
      setState(() {
        final message = e.message ?? e.code;
        _errorMessage = '匿名認証に失敗しました (${e.code}): $message';
      });
    } catch (e, st) {
      debugPrint('Anonymous sign-in threw an unexpected error: $e');
      debugPrintStack(stackTrace: st);
      if (!mounted) return;
      setState(() {
        _errorMessage = '匿名認証に失敗しました: $e';
      });
    } finally {
      if (!mounted) return;
      setState(() {
        _isSigningIn = false;
      });
    }
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
    if (_isSending) {
      return;
    }

    if (_userId == null) {
      await _ensureSignedIn();
      if (_userId == null) {
        setState(() {
          _errorMessage = 'ユーザーIDの取得に失敗しました。アプリを再起動して再試行してください。';
        });
        return;
      }
    }

    if (!_isPermissionGranted) {
      await _requestPermission();
      if (!_isPermissionGranted) {
        setState(() {
          _errorMessage = 'カメラ権限が必要です。設定から許可してください。';
        });
        return;
      }
    }

    var controller = _controller;
    if (controller == null || !controller.value.isInitialized) {
      await _initializeCamera();
      controller = _controller;
    }
    if (controller == null || !controller.value.isInitialized) {
      return;
    }
    setState(() {
      _isSending = true;
    });
    try {
      final file = await controller.takePicture();
      final imageFile = File(file.path);
      final payloadSize = await imageFile.length();

      final uploadResult = await _uploadAndRecord(imageFile, _userId!);

      if (!mounted) return;
      setState(() {
        _lastSentAt = DateTime.now();
        _lastPayloadSize = payloadSize;
        _lastStoragePath = uploadResult.storagePath;
        _lastDownloadUrl = uploadResult.downloadUrl;
      });
    } on FirebaseException catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessage = 'クラウド保存に失敗しました: ${e.message ?? e.code}';
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

  Future<({String storagePath, String downloadUrl})> _uploadAndRecord(
    File imageFile,
    String userId,
  ) async {
    final fileName =
        '${DateTime.now().toUtc().toIso8601String().replaceAll(':', '-')}_${_randomString(6)}.jpg';
    final storagePath = 'users/$userId/captures/$fileName';
    final ref = FirebaseStorage.instance.ref().child(storagePath);
    await ref.putFile(imageFile);
    final downloadUrl = await ref.getDownloadURL();
    await FirebaseFirestore.instance
        .collection('users')
        .doc(userId)
        .collection('captures')
        .add({
      'storagePath': storagePath,
      'downloadUrl': downloadUrl,
      'userId': userId,
      'createdAt': FieldValue.serverTimestamp(),
    });
    return (storagePath: storagePath, downloadUrl: downloadUrl);
  }

  String _randomString(int length) {
    const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
    return String.fromCharCodes(
      Iterable.generate(
        length,
        (_) => chars.codeUnitAt(_random.nextInt(chars.length)),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final controller = _controller;
    final permissionLabel = () {
      if (_permissionStatus == null) return '未確認';
      if (_isPermissionGranted) return '許可済み';
      if (_permissionStatus!.isPermanentlyDenied) {
        return '永久に拒否（設定アプリから許可してください）';
      }
      return '未許可';
    }();

    return Scaffold(
      appBar: AppBar(title: Text(widget.title)),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'カメラ権限: $permissionLabel',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 8),
              Card(
                child: ListTile(
                  leading: const Icon(Icons.person_outline),
                  title: const Text('ユーザーID'),
                  subtitle: Text(
                    _userId ??
                        (_isSigningIn
                            ? '匿名認証中…'
                            : '未取得（再初期化してください）'),
                  ),
                  trailing:
                      _userId != null ? const Icon(Icons.copy_rounded) : null,
                  onTap: _userId == null
                      ? null
                      : () async {
                          await Clipboard.setData(
                            ClipboardData(text: _userId!),
                          );
                          if (!mounted) return;
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Text('ユーザーIDをコピーしました'),
                              duration: Duration(seconds: 1),
                            ),
                          );
                        },
                ),
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
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Icon(Icons.autorenew, size: 18),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                '10秒ごとに自動撮影し、Cloud Storageへ保存します。',
                                style: Theme.of(context).textTheme.bodyMedium,
                              ),
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
                        if (_lastStoragePath != null)
                          Text(
                            '保存先: $_lastStoragePath',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        if (_lastDownloadUrl != null)
                          Text(
                            'URL: $_lastDownloadUrl',
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
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                  ),
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
