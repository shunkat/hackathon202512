import 'dart:math';

import 'package:client/capture_utils.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('generateRandomString', () {
    test('指定した長さの英数字を生成する', () {
      final result = generateRandomString(8, Random(1));

      expect(result, hasLength(8));
      expect(result, matches(RegExp(r'^[a-z0-9]+$')));
    });

    test('同じシード値なら決定的な結果になる', () {
      final first = generateRandomString(10, Random(42));
      final second = generateRandomString(10, Random(42));
      final differentSeed = generateRandomString(10, Random(99));

      expect(first, equals(second));
      expect(first, isNot(equals(differentSeed)));
    });
  });

  group('buildCaptureFileName', () {
    test('UTCタイムスタンプと乱数を含むファイル名を返す', () {
      final now = DateTime.utc(2024, 12, 31, 23, 59, 59, 123);
      final fileName = buildCaptureFileName(
        now,
        Random(7),
        randomLength: 4,
      );

      expect(fileName, startsWith('2024-12-31T23-59-59.123Z_'));
      expect(fileName, endsWith('.jpg'));

      final suffix = fileName
          .replaceFirst('2024-12-31T23-59-59.123Z_', '')
          .replaceFirst('.jpg', '');
      expect(suffix, hasLength(4));
      expect(suffix, matches(RegExp(r'^[a-z0-9]{4}$')));
    });
  });
}
