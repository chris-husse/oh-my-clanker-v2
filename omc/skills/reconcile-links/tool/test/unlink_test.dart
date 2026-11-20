import 'package:docs_links/docs_links.dart';
import 'package:test/test.dart';

void main() {
  group('unlink', () {
    test('a link becomes its text', () {
      expect(unlink('See [W16](../stories/worker.md#W16%20—%20A%20replacement%20phone) now.'), 'See W16 now.');
    });
    test('a same-file link becomes its text', () {
      expect(unlink('[9.18](#9.18%20Device%20kill%20is%20an%20emergency%20act)'), '9.18');
    });
    test('balanced parentheses stay inside the destination', () {
      expect(unlink('[x](a.md#Check%20In%20(QR):%20confirm) y'), 'x y');
    });
    test('a pinned link becomes its text; the title goes with the link', () {
      expect(unlink('See [S10](stories/supervisor.md#S10%20—%20Review%20a%20petition "git:0f1211d1a2b3") now.'), 'See S10 now.');
    });
    test('images stay', () {
      expect(unlink('![shot](../shots/en/a.png)'), '![shot](../shots/en/a.png)');
    });
    test('links in code stay', () {
      expect(unlink('`[a](b.md)` and\n```\n[c](d.md)\n```\n'), '`[a](b.md)` and\n```\n[c](d.md)\n```\n');
    });
    test('text without links is returned unchanged', () {
      const s = '### W16 — A replacement phone\n\n**Sees.** Everything (W2, 14.26).\n';
      expect(unlink(s), s);
    });
  });

  group('mask', () {
    test('keeps every newline and the length', () {
      const s = 'a `code` b\n```\nx\n```\n<!-- c\nd -->e';
      final m = mask(s);
      expect(m.length, s.length);
      expect('\n'.allMatches(m).length, '\n'.allMatches(s).length);
      expect(m.contains('code') || m.contains('x') || m.contains('c\nd'), isFalse);
      expect(m.endsWith('e'), isTrue);
    });
  });

  group('headings and anchors', () {
    test('headings outside code, with their raw text', () {
      final hs = headingsOf('# T\n\n```\n# not\n```\n### W16 — A `x` phone\n');
      expect([for (final h in hs) h.text], ['T', 'W16 — A `x` phone']);
      expect(hs.last.line, 6);
    });
    test('an anchor is the text with spaces as %20, everything else raw', () {
      expect(encodeAnchor('6. Where tasks come from, in 00 §4.3 and 03 §3'),
          '6.%20Where%20tasks%20come%20from,%20in%2000%20§4.3%20and%2003%20§3');
    });
    test('the GitHub slug keeps letters with accents', () {
      expect(githubSlug('1.1.3 Un teléfono de reemplazo'), '113-un-teléfono-de-reemplazo');
    });
  });
}
