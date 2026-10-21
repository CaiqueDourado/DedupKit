using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;

namespace DedupKit;

/// <summary>
/// Attributes written in product names (size, voltage, memory, colour, gender) and conflicts between
/// them. Two listings with the same barcode or photo are not the same product when one says 2,5kg and
/// the other 15kg.
/// </summary>
public static class ProductAttributes
{
    private static readonly (string Unit, string Dimension, decimal Factor)[] Units =
    {
        ("kg", "weight_kg", 1m), ("kgs", "weight_kg", 1m), ("g", "weight_kg", 0.001m), ("gr", "weight_kg", 0.001m),
        ("mg", "weight_kg", 0.000001m), ("l", "volume_l", 1m), ("lt", "volume_l", 1m), ("litro", "volume_l", 1m),
        ("litros", "volume_l", 1m), ("ml", "volume_l", 0.001m), ("v", "voltage_v", 1m), ("w", "power_w", 1m),
        ("kw", "power_w", 1000m), ("gb", "memory_gb", 1m), ("tb", "memory_gb", 1000m), ("mb", "memory_gb", 0.001m),
        ("mah", "battery_mah", 1m), ("mm", "length_cm", 0.1m), ("cm", "length_cm", 1m), ("m", "length_cm", 100m),
        ("pol", "screen_in", 1m), ("polegadas", "screen_in", 1m), ("polegada", "screen_in", 1m),
        ("btu", "cooling_btu", 1m), ("btus", "cooling_btu", 1m),
    };

    private static readonly Dictionary<string, string> Colours = new(StringComparer.Ordinal)
    {
        ["preto"] = "preto", ["preta"] = "preto", ["branco"] = "branco", ["branca"] = "branco", ["azul"] = "azul",
        ["vermelho"] = "vermelho", ["vermelha"] = "vermelho", ["verde"] = "verde", ["amarelo"] = "amarelo",
        ["amarela"] = "amarelo", ["rosa"] = "rosa", ["cinza"] = "cinza", ["grafite"] = "grafite", ["inox"] = "inox",
        ["prata"] = "prata", ["prateado"] = "prata", ["prateada"] = "prata", ["dourado"] = "dourado",
        ["dourada"] = "dourado", ["cobre"] = "cobre", ["bege"] = "bege", ["marrom"] = "marrom", ["roxo"] = "roxo",
        ["roxa"] = "roxo", ["laranja"] = "laranja", ["chumbo"] = "chumbo", ["transparente"] = "transparente",
        ["nude"] = "nude", ["lilas"] = "lilas", ["vinho"] = "vinho",
    };

    private static readonly Dictionary<string, string> Genders = new(StringComparer.Ordinal)
    {
        ["masculino"] = "masculino", ["masculina"] = "masculino", ["feminino"] = "feminino",
        ["feminina"] = "feminino", ["infantil"] = "infantil", ["unissex"] = "unissex",
    };

    private static readonly Regex Measure = new(
        "(?<![a-z0-9])([0-9]+(?:[.,][0-9]+)?) ?(" +
        string.Join('|', Units.Select(u => u.Unit).OrderByDescending(u => u.Length)) +
        ")(?![a-z0-9])",
        RegexOptions.CultureInvariant | RegexOptions.Compiled);

    private static string Fold(string? text)
    {
        var sb = new StringBuilder();
        foreach (var ch in text ?? string.Empty)
        {
            if (FoldTable.Fold.TryGetValue(ch, out var mapped))
            {
                sb.Append(mapped);
            }
            else if (ch is >= 'A' and <= 'Z')
            {
                sb.Append((char)(ch + 32));
            }
            else if (ch is >= 'a' and <= 'z' or >= '0' and <= '9' or '.' or ',')
            {
                sb.Append(ch);
            }
            else
            {
                sb.Append(' ');
            }
        }

        return string.Join(' ', sb.ToString().Split(' ', StringSplitOptions.RemoveEmptyEntries));
    }

    private static string Canonical(string number, decimal factor)
    {
        // "12.000 BTUs" and "7.500W": a dot followed by exactly three digits separates thousands
        var dot = number.IndexOf('.', StringComparison.Ordinal);
        if (dot >= 0 && number.Length - dot - 1 == 3)
        {
            number = number.Replace(".", string.Empty, StringComparison.Ordinal);
        }

        var value = decimal.Parse(number.Replace(',', '.'), NumberStyles.AllowDecimalPoint, CultureInfo.InvariantCulture) * factor;
        return value.ToString("0.############################", CultureInfo.InvariantCulture);
    }

    /// <summary>
    /// Measures, colours and gender found in a name. "Ração 2,5kg" → weight_kg: {2.5}; "500g" and
    /// "0,5 kg" give the same value. "Bivolt" makes the voltage unknown.
    /// </summary>
    public static IReadOnlyDictionary<string, IReadOnlySet<string>> Extract(string? text)
    {
        var folded = Fold(text);
        var found = new SortedDictionary<string, HashSet<string>>(StringComparer.Ordinal);
        foreach (Match m in Measure.Matches(folded))
        {
            var unit = Units.First(u => u.Unit == m.Groups[2].Value);
            if (!found.TryGetValue(unit.Dimension, out var set))
            {
                set = new HashSet<string>(StringComparer.Ordinal);
                found[unit.Dimension] = set;
            }

            set.Add(Canonical(m.Groups[1].Value, unit.Factor));
        }

        var words = folded.Replace('.', ' ').Replace(',', ' ').Split(' ', StringSplitOptions.RemoveEmptyEntries).ToHashSet(StringComparer.Ordinal);
        if (words.Contains("bivolt"))
        {
            found.Remove("voltage_v");
        }

        var colours = words.Where(Colours.ContainsKey).Select(w => Colours[w]).ToHashSet(StringComparer.Ordinal);
        if (colours.Count > 0)
        {
            found["colour"] = colours;
        }

        var genders = words.Where(Genders.ContainsKey).Select(w => Genders[w]).ToHashSet(StringComparer.Ordinal);
        if (genders.Count > 0)
        {
            found["gender"] = genders;
        }

        return found.ToDictionary(kv => kv.Key, kv => (IReadOnlySet<string>)kv.Value, StringComparer.Ordinal);
    }

    /// <summary>
    /// The first attribute on which two names disagree, or null. Both names must state the attribute
    /// and share no value: "110V" vs "110V/220V" is not a conflict.
    /// </summary>
    public static string? Conflict(string? a, string? b) => Conflict(Extract(a), Extract(b));

    /// <summary><see cref="Conflict(string?, string?)"/> on attributes already extracted.</summary>
    public static string? Conflict(IReadOnlyDictionary<string, IReadOnlySet<string>> a, IReadOnlyDictionary<string, IReadOnlySet<string>> b)
    {
        foreach (var dim in a.Keys.Intersect(b.Keys, StringComparer.Ordinal).OrderBy(k => k, StringComparer.Ordinal))
        {
            if (!a[dim].Overlaps(b[dim]))
            {
                static string Join(IEnumerable<string> v) => string.Join('/', v.OrderBy(x => x, StringComparer.Ordinal));
                return $"{dim}: {Join(a[dim])} vs {Join(b[dim])}";
            }
        }

        return null;
    }
}
