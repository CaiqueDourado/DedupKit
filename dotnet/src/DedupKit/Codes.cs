namespace DedupKit;

/// <summary>Product codes (EAN/GTIN, SKU) as stores really fill them in.</summary>
public static class Codes
{
    private static readonly HashSet<string> Placeholders = new(
        new[] { "SEMGTIN", "SEMEAN", "NULL", "NONE", "NA", "N/A", "#N/A", "---", "-", "0", "1000000000000" },
        StringComparer.Ordinal);

    private static bool AsciiDigits(string s) => s.Length > 0 && s.All(c => c is >= '0' and <= '9');

    /// <summary>ASCII letters in upper case; spaces, dashes and dots removed: " 789-1234 " → "7891234".</summary>
    public static string Clean(string? value)
    {
        var sb = new System.Text.StringBuilder();
        foreach (var ch in value ?? string.Empty)
        {
            if (ch is ' ' or '\t' or '\r' or '\n' or '-' or '.')
            {
                continue;
            }

            sb.Append(ch is >= 'a' and <= 'z' ? (char)(ch - 32) : ch);
        }

        return sb.ToString();
    }

    /// <summary>GTIN-8, -12, -13 or -14 with a correct check digit.</summary>
    public static bool IsValidGtin(string? code)
    {
        var c = Clean(code);
        if (c.Length is not (8 or 12 or 13 or 14) || !AsciiDigits(c))
        {
            return false;
        }

        var total = 0;
        for (var i = 0; i < c.Length - 1; i++)
        {
            var digit = c[c.Length - 2 - i] - '0';
            total += digit * (i % 2 == 0 ? 3 : 1);
        }

        return (10 - total % 10) % 10 == c[^1] - '0';
    }

    /// <summary>"SEM GTIN", "0", all zeros, "N/A" and numbers mangled by spreadsheets ("7.89E+12").</summary>
    public static bool IsPlaceholder(string? code)
    {
        var c = Clean(code);
        if (c.Length == 0 || Placeholders.Contains(c) || c.All(ch => ch == '0'))
        {
            return true;
        }

        return c.Contains('+', StringComparison.Ordinal);
    }

    /// <summary>
    /// "long", "short", "placeholder" or "invalid". A numeric code is long when it has 7 or more
    /// digits and at least 6 of them remain after leading zeros are removed. Short codes only count
    /// together with the brand.
    /// </summary>
    public static string Classify(string? code)
    {
        var c = Clean(code);
        if (IsPlaceholder(c))
        {
            return "placeholder";
        }

        if (AsciiDigits(c))
        {
            var significant = c.TrimStart('0').Length;
            if (c.Length >= 7)
            {
                return significant >= 6 ? "long" : "short";
            }

            return c.Length >= 4 ? "short" : "invalid";
        }

        if (c.Length >= 5)
        {
            return "long";
        }

        return c.Length >= 3 ? "short" : "invalid";
    }
}
