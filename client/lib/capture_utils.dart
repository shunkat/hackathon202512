import 'dart:math';

/// 撮影ファイル名の乱数部分を生成する。
String generateRandomString(int length, Random random) {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  return String.fromCharCodes(
    Iterable.generate(
      length,
      (_) => chars.codeUnitAt(random.nextInt(chars.length)),
    ),
  );
}

/// UTCタイムスタンプと乱数から撮影用のファイル名を組み立てる。
String buildCaptureFileName(
  DateTime now,
  Random random, {
  int randomLength = 6,
}) {
  final timestamp = now.toUtc().toIso8601String().replaceAll(':', '-');
  final randomSuffix = generateRandomString(randomLength, random);
  return '$timestamp\_$randomSuffix.jpg';
}
