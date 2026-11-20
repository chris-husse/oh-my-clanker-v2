import 'scan.dart';
import 'text.dart';

/// [text] with every inline link (not image) replaced by its text: how the corpus reads to a program.
String unlink(String text) {
  final links = scanLinks(mask(text)).where((l) => !l.image);
  final b = StringBuffer();
  var at = 0;
  for (final l in links) {
    b
      ..write(text.substring(at, l.start))
      ..write(text.substring(l.textStart, l.textEnd));
    at = l.end;
  }
  b.write(text.substring(at));
  return b.toString();
}
