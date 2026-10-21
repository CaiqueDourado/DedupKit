using System.Text.Json;

namespace DedupKit.Tests;

/// <summary>testdata/golden.json comes from the Python package; every value must match exactly.</summary>
public class GoldenTests
{
    private static readonly JsonElement Root = JsonDocument.Parse(
        File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "testdata", "golden.json"))).RootElement;

    public static IEnumerable<object[]> Texts() =>
        Enumerable.Range(0, Root.GetProperty("texts").GetArrayLength()).Select(i => new object[] { i });

    public static IEnumerable<object[]> ResultKeys() =>
        Root.GetProperty("results").EnumerateObject().Select(p => new object[] { p.Name });

    [Theory]
    [MemberData(nameof(Texts))]
    public void TextKeysMatch(int index)
    {
        var c = Root.GetProperty("texts")[index];
        var t = c.GetProperty("text").GetString()!;
        var other = c.GetProperty("other").GetString()!;
        Assert.Equal(c.GetProperty("normalize").GetString(), TextKeys.Normalize(t));
        Assert.Equal(c.GetProperty("fingerprint").GetString(), TextKeys.Fingerprint(t));
        Assert.Equal(c.GetProperty("legacy_fingerprint").GetString(), TextKeys.LegacyFingerprint(t));
        Assert.Equal(c.GetProperty("ngram2").GetString(), TextKeys.NgramFingerprint(t));
        Assert.Equal(c.GetProperty("ngram3").GetString(), TextKeys.NgramFingerprint(t, 3));
        Assert.Equal(c.GetProperty("token_key").GetString(), TextKeys.TokenKey(t));
        Assert.Equal(c.GetProperty("phonetic").GetString(), TextKeys.PhoneticKey(t));
        Assert.Equal(c.GetProperty("shares_word").GetBoolean(), TextKeys.SharesWord(t, other));
        var conflict = c.GetProperty("conflict");
        Assert.Equal(conflict.ValueKind == JsonValueKind.Null ? null : conflict.GetString(), ProductAttributes.Conflict(t, other));

        var expected = c.GetProperty("attributes").EnumerateObject()
            .Select(p => p.Name + "=" + string.Join("/", p.Value.EnumerateArray().Select(v => v.GetString())));
        var actual = ProductAttributes.Extract(t).OrderBy(kv => kv.Key, StringComparer.Ordinal)
            .Select(kv => kv.Key + "=" + string.Join("/", kv.Value.OrderBy(v => v, StringComparer.Ordinal)));
        Assert.Equal(string.Join(";", expected), string.Join(";", actual));
    }

    [Fact]
    public void SingularCodesAndUrlsMatch()
    {
        foreach (var p in Root.GetProperty("singular").EnumerateObject())
        {
            Assert.Equal(p.Value.GetString(), TextKeys.Singular(p.Name));
        }

        foreach (var c in Root.GetProperty("codes").EnumerateArray())
        {
            var code = c.GetProperty("code").GetString()!;
            Assert.Equal(c.GetProperty("clean").GetString(), Codes.Clean(code));
            Assert.Equal(c.GetProperty("valid_gtin").GetBoolean(), Codes.IsValidGtin(code));
            Assert.Equal(c.GetProperty("placeholder").GetBoolean(), Codes.IsPlaceholder(code));
            Assert.Equal(c.GetProperty("class").GetString(), Codes.Classify(code));
        }

        foreach (var p in Root.GetProperty("urls").EnumerateObject())
        {
            Assert.Equal(p.Value.GetString(), TextKeys.NormalizeUrl(p.Name));
        }
    }

    [Theory]
    [MemberData(nameof(ResultKeys))]
    public void MatchResultsMatch(string key)
    {
        var records = Root.GetProperty("listings").EnumerateArray().Select(l => new Record(
            l.GetProperty("id").GetString()!, l.GetProperty("name").GetString()!, l.GetProperty("brand").GetString()!,
            l.GetProperty("codes").EnumerateArray().Select(x => x.GetString()!).ToList(),
            l.GetProperty("url").GetString()!, l.GetProperty("image").GetString()!, l.GetProperty("source").GetString()!)).ToList();

        var parts = key.Split('|');
        var mode = parts[0] == "connected" ? MatchMode.Connected : MatchMode.TwoHop;
        var option = parts[1];
        var options = option switch
        {
            "attributes=True" => new MatchOptions { Mode = mode },
            "attributes=False" => new MatchOptions { Mode = mode, CheckAttributes = false },
            "brands" => new MatchOptions { Mode = mode, CheckBrands = true },
            "legacy" => new MatchOptions { Mode = mode, Rules = Rules.Legacy, CheckAttributes = false },
            _ => new MatchOptions { Mode = mode, MaxBlock = int.Parse(option.Split('=')[1], System.Globalization.CultureInfo.InvariantCulture) },
        };
        var r = Matcher.Match(records, options);
        var e = Root.GetProperty("results").GetProperty(key);

        foreach (var p in e.GetProperty("cluster_of").EnumerateObject())
        {
            Assert.Equal(p.Value.GetInt32(), r.ClusterOf[p.Name]);
        }

        Assert.Equal(e.GetProperty("via").EnumerateObject().Count(), r.Via.Count);
        foreach (var p in e.GetProperty("via").EnumerateObject())
        {
            Assert.Equal(p.Value[0].GetString() + "|" + p.Value[1].GetString(), r.Via[p.Name].Rule + "|" + r.Via[p.Name].Value);
        }

        static string Rows(IEnumerable<IEnumerable<string>> rows) => string.Join("\n", rows.Select(x => string.Join("\t", x)));
        Assert.Equal(Rows(e.GetProperty("links").EnumerateArray().Select(a => a.EnumerateArray().Select(x => x.GetString()!))),
            Rows(r.Links.Select(l => new[] { l.A, l.B, l.Rule, l.Value })));
        Assert.Equal(Rows(e.GetProperty("rejected").EnumerateArray().Select(a => a.EnumerateArray().Select(x => x.GetString()!))),
            Rows(r.Rejected.Select(x => new[] { x.A, x.B, x.Rule, x.Value, x.Reason })));
        Assert.Equal(Rows(e.GetProperty("skipped").EnumerateArray().Select(a => a.EnumerateArray().Select(x => x.ValueKind == JsonValueKind.Number ? x.GetInt32().ToString(System.Globalization.CultureInfo.InvariantCulture) : x.GetString()!))),
            Rows(r.Skipped.Select(s => new[] { s.Rule, s.Value, s.Size.ToString(System.Globalization.CultureInfo.InvariantCulture) })));
    }
}
