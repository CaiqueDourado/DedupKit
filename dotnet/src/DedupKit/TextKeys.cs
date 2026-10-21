using System.Text;
using System.Text.RegularExpressions;

namespace DedupKit;

/// <summary>
/// Text keys for matching: normalization, fingerprints, n-grams, plural reduction and a
/// Portuguese phonetic key. Identical to the Python package (see spec/ALGORITHMS.md);
/// no Unicode normalization or culture is used, so results do not depend on ICU.
/// </summary>
public static class TextKeys
{
    /// <summary>Portuguese function words ignored by <see cref="TokenKey"/> and <see cref="SharesWord"/>.</summary>
    public static readonly IReadOnlySet<string> Stopwords = new HashSet<string>(
        "a o as os um uma uns umas de da do das dos em na no nas nos e ou com sem para pra pro por pelo pela pelos pelas ao aos que se c p s".Split(' '),
        StringComparer.Ordinal);

    private static readonly HashSet<string> PluralSame = new(
        ("mais menos pires lapis cais tenis onibus virus bonus campus atlas gas atras apos ambas ambos depois pois dois tres seis " +
         "simples oculos jeans gratis pais mas oasis iris chassis vies ferias parabens alias lotus lens bis status").Split(' '),
        StringComparer.Ordinal);

    private static readonly Dictionary<string, string> PluralIrregular = new(StringComparer.Ordinal)
    {
        ["maes"] = "mae", ["reis"] = "rei", ["leis"] = "lei", ["bois"] = "boi", ["herois"] = "heroi",
        ["biquinis"] = "biquini", ["bikinis"] = "bikini", ["taxis"] = "taxi", ["jacuzzis"] = "jacuzzi",
    };

    private static readonly HashSet<string> TrackingParams = new(
        ("gclid fbclid msclkid dclid ref ref_ source origem origin campaign cmp partner parceiro afiliado affiliate awc zanpid " +
         "lmdsid chave opn epar franq s_kwcid tag srsltid _ga mc_cid mc_eid").Split(' '),
        StringComparer.Ordinal);

    private static readonly (Regex Pattern, string Replacement)[] PhoneticRules =
    {
        (R("^h"), ""),
        (R("ch"), "x"), (R("sh"), "x"), (R("ph"), "f"), (R("th"), "t"),
        (R("lh"), "1"), (R("nh"), "3"),
        (R("h"), ""),
        (R("rr"), "2"), (R("^r"), "2"), (R("(?<=[nls])r"), "2"),
        (R("(?<=[aeiou])s(?=[aeiou])"), "z"),
        (R("ss"), "s"),
        (R("sc(?=[eiy])"), "s"), (R("xc(?=[eiy])"), "s"),
        (R("g(?=[eiy])"), "j"),
        (R("qu(?=[eiy])"), "k"), (R("gu(?=[eiy])"), "g"), (R("q"), "k"),
        (R("c(?=[eiy])"), "s"), (R("c"), "k"),
        (R("y"), "i"), (R("w"), "v"),
        (R("^ex(?=[aeiou])"), "ez"),
        (R("z$"), "s"),
        (R("n(?=[bcdfgjklmpqstvxz2])"), "m"), (R("n$"), "m"),
        (R("l(?=[bcdfgjkmnpqstvxz23]|$)"), "u"),
    };

    private static readonly Regex Repeat = R("([a-z])\\1+");

    private static Regex R(string pattern) => new(pattern, RegexOptions.CultureInvariant | RegexOptions.Compiled);

    private static string FoldChar(char ch, bool phonetic)
    {
        if (phonetic && ch is 'ç' or 'Ç')
        {
            return "ss";
        }

        if (FoldTable.Fold.TryGetValue(ch, out var mapped))
        {
            return mapped;
        }

        if (ch is >= 'A' and <= 'Z')
        {
            return ((char)(ch + 32)).ToString();
        }

        if (ch is >= 'a' and <= 'z' or >= '0' and <= '9')
        {
            return ch.ToString();
        }

        if (ch is >= '̀' and <= 'ͯ')
        {
            return string.Empty;
        }

        return " ";
    }

    private static string Normalize(string? text, bool phonetic)
    {
        if (string.IsNullOrEmpty(text))
        {
            return string.Empty;
        }

        var sb = new StringBuilder(text.Length);
        foreach (var ch in text)
        {
            sb.Append(FoldChar(ch, phonetic));
        }

        return string.Join(' ', sb.ToString().Split(' ', StringSplitOptions.RemoveEmptyEntries));
    }

    /// <summary>
    /// Lower case, accents removed (ç → c), anything that is not a letter or digit becomes a space,
    /// spaces collapsed. "Pendente TLF-28, Preto!" → "pendente tlf 28 preto".
    /// </summary>
    public static string Normalize(string? text) => Normalize(text, false);

    /// <summary>Words of the normalized text, in order.</summary>
    public static string[] Tokens(string? text)
    {
        var n = Normalize(text);
        return n.Length == 0 ? Array.Empty<string>() : n.Split(' ');
    }

    private static string SortedUnique(IEnumerable<string> words) =>
        string.Join(' ', words.Distinct(StringComparer.Ordinal).OrderBy(w => w, StringComparer.Ordinal));

    /// <summary>Unique words, sorted (OpenRefine-style fingerprint).</summary>
    public static string Fingerprint(string? text) => SortedUnique(Tokens(text));

    /// <summary>
    /// The 2019 pipeline's fingerprint, bug included: after sorting it kept only every other word.
    /// Only for reproducing old results.
    /// </summary>
    public static string LegacyFingerprint(string? text)
    {
        var words = Tokens(text).Distinct(StringComparer.Ordinal).OrderBy(w => w, StringComparer.Ordinal).ToArray();
        var sb = new StringBuilder();
        for (var i = 0; i < words.Length; i += 2)
        {
            sb.Append(words[i]);
            if (i + 1 < words.Length)
            {
                sb.Append(' ');
            }
        }

        return sb.ToString();
    }

    /// <summary>
    /// OpenRefine-style n-gram fingerprint: the normalized text without spaces, cut into character
    /// n-grams, unique and sorted, concatenated.
    /// </summary>
    public static string NgramFingerprint(string? text, int n = 2)
    {
        if (n < 1)
        {
            throw new ArgumentOutOfRangeException(nameof(n), "n must be positive.");
        }

        var s = Normalize(text).Replace(" ", string.Empty, StringComparison.Ordinal);
        if (s.Length < n)
        {
            return s;
        }

        var grams = new HashSet<string>(StringComparer.Ordinal);
        for (var i = 0; i + n <= s.Length; i++)
        {
            grams.Add(s.Substring(i, n));
        }

        return string.Concat(grams.OrderBy(g => g, StringComparer.Ordinal));
    }

    /// <summary>
    /// Reduces a normalized Portuguese plural to the singular (rules adapted from the RSLP plural
    /// step, Orengo and Huyck 2001, for text without accents).
    /// </summary>
    public static string Singular(string word)
    {
        ArgumentNullException.ThrowIfNull(word);
        var w = word;
        if (w.Length < 4 || !w.EndsWith('s') || PluralSame.Contains(w))
        {
            return w;
        }

        if (PluralIrregular.TryGetValue(w, out var irregular))
        {
            return irregular;
        }

        static bool Ends(string s, string suffix) => s.EndsWith(suffix, StringComparison.Ordinal);
        static bool Vowel(char c) => c is 'a' or 'e' or 'i' or 'o' or 'u';

        if (Ends(w, "ns"))
        {
            return w[..^2] + "m";
        }

        if (Ends(w, "oes") || Ends(w, "aes"))
        {
            return w[..^3] + "ao";
        }

        if (Ends(w, "ais"))
        {
            return w[..^3] + "al";
        }

        if (Ends(w, "eis"))
        {
            return w[..^3] + "el";
        }

        if (Ends(w, "ois"))
        {
            return w[..^3] + "ol";
        }

        if (Ends(w, "is") && w.Length >= 5 && w[^3] is 'n' or 'r' or 'z' or 'f')
        {
            return w[..^2] + "il";
        }

        if (Ends(w, "res") && Vowel(w[^4]))
        {
            return w[..^2];
        }

        if (Ends(w, "zes") && Vowel(w[^4]))
        {
            return w[..^2];
        }

        if (Ends(w, "ss") || Ends(w, "us") || Ends(w, "is"))
        {
            return w;
        }

        return w[..^1];
    }

    /// <summary>Words without stopwords, reduced to the singular, unique and sorted.</summary>
    public static string TokenKey(string? text) =>
        SortedUnique(Tokens(text).Where(t => !Stopwords.Contains(t)).Select(Singular));

    /// <summary>
    /// Phonetic key of one normalized word, written for Brazilian Portuguese: "cassarola" and
    /// "caçarola" → "KSRL"; "chuveiro" and "xuveiro" → "XVR".
    /// </summary>
    public static string PhoneticWord(string word)
    {
        ArgumentNullException.ThrowIfNull(word);
        if (word.Length == 0)
        {
            return string.Empty;
        }

        if (word.All(c => c is >= '0' and <= '9'))
        {
            return word;
        }

        var w = word;
        foreach (var (pattern, replacement) in PhoneticRules)
        {
            w = pattern.Replace(w, replacement);
        }

        if (w.Length == 0)
        {
            return string.Empty;
        }

        var sb = new StringBuilder();
        sb.Append(w[0]);
        foreach (var c in w.AsSpan(1))
        {
            if (c is not ('a' or 'e' or 'i' or 'o' or 'u'))
            {
                sb.Append(c);
            }
        }

        return Repeat.Replace(sb.ToString(), "$1").ToUpperInvariant();
    }

    /// <summary>Phonetic key of each word, in the original order.</summary>
    public static string PhoneticKey(string? text)
    {
        var words = Normalize(text, true).Split(' ', StringSplitOptions.RemoveEmptyEntries); // ç is read as ss here
        return string.Join(' ', words.Select(PhoneticWord).Where(k => k.Length > 0));
    }

    /// <summary>
    /// Lower case (ASCII letters), without scheme, www., fragment, trailing slash and tracking
    /// parameters (utm_*, gclid, affiliate ids...). Other parameters stay, sorted.
    /// </summary>
    public static string NormalizeUrl(string? url)
    {
        var sb = new StringBuilder();
        foreach (var c in (url ?? string.Empty).Trim(' ', '\t', '\r', '\n'))
        {
            sb.Append(c is >= 'A' and <= 'Z' ? (char)(c + 32) : c);
        }

        var u = Regex.Replace(sb.ToString(), "^[a-z][a-z0-9+.-]*://", string.Empty, RegexOptions.CultureInvariant);
        u = Regex.Replace(u, "^www\\.", string.Empty, RegexOptions.CultureInvariant);
        var hash = u.IndexOf('#', StringComparison.Ordinal);
        if (hash >= 0)
        {
            u = u[..hash];
        }

        var q = u.IndexOf('?', StringComparison.Ordinal);
        var path = (q >= 0 ? u[..q] : u).TrimEnd('/');
        var query = q >= 0 ? u[(q + 1)..] : string.Empty;
        var kept = new List<string>();
        foreach (var part in query.Split('&'))
        {
            if (part.Length == 0)
            {
                continue;
            }

            var eq = part.IndexOf('=', StringComparison.Ordinal);
            var key = eq >= 0 ? part[..eq] : part;
            if (key.StartsWith("utm_", StringComparison.Ordinal) || TrackingParams.Contains(key))
            {
                continue;
            }

            kept.Add(part);
        }

        kept.Sort(StringComparer.Ordinal);
        return kept.Count > 0 ? path + "?" + string.Join('&', kept) : path;
    }

    /// <summary>
    /// True when the two texts share a word (or one word contains the other, from 3 letters on),
    /// ignoring stopwords and one-letter words.
    /// </summary>
    public static bool SharesWord(string? a, string? b)
    {
        var ta = Tokens(a).Where(t => t.Length > 1 && !Stopwords.Contains(t)).ToHashSet(StringComparer.Ordinal);
        var tb = Tokens(b).Where(t => t.Length > 1 && !Stopwords.Contains(t)).ToHashSet(StringComparer.Ordinal);
        if (ta.Overlaps(tb))
        {
            return true;
        }

        foreach (var x in ta)
        {
            foreach (var y in tb)
            {
                if (x.Length >= 3 && y.Length >= 3 &&
                    (y.Contains(x, StringComparison.Ordinal) || x.Contains(y, StringComparison.Ordinal)))
                {
                    return true;
                }
            }
        }

        return false;
    }
}
