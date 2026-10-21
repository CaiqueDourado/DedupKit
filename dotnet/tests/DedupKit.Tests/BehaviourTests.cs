namespace DedupKit.Tests;

public class BehaviourTests
{
    private static List<Record> Sample() => new()
    {
        new("a", "Guitarra Strinberg Preta", Codes: new[] { "7891234567895" }),
        new("b", "Reservatório de água Gol", Codes: new[] { "7891234567895" }),
        new("c", "Guitarra Strinberg STS100 preta", Codes: new[] { "7891234567895" }),
        new("d", "Guitarra Strinberg STS100 Preto"),
        new("e", "Ração Golden 15kg", Codes: new[] { "7894904567891" }),
        new("f", "Ração Golden 2,5kg", Codes: new[] { "7894904567891" }),
    };

    [Theory]
    [InlineData(MatchMode.Connected)]
    [InlineData(MatchMode.TwoHop)]
    public void BarcodeNeedsSharedWordAndSameSize(MatchMode mode)
    {
        var r = Matcher.Match(Sample(), new MatchOptions { Mode = mode });
        var cluster = Assert.Single(r.Clusters);
        Assert.Equal(new[] { "a", "c", "d" }, cluster);
        Assert.Contains(r.Rejected, x => x.A == "a" && x.B == "b" && x.Reason == "names share no word");
        Assert.Contains(r.Rejected, x => x.A == "e" && x.B == "f" && x.Reason.StartsWith("weight_kg", StringComparison.Ordinal));
    }

    [Fact]
    public void TextExamples()
    {
        Assert.Equal("pendente tlf 28 preto", TextKeys.Normalize("Pendente TLF-28, Preto!"));
        Assert.Equal("fio fone ouvido", TextKeys.TokenKey("Fones de Ouvido sem Fio"));
        Assert.Equal(TextKeys.PhoneticKey("cassarola"), TextKeys.PhoneticKey("Caçarola"));
        Assert.Equal("a c ", TextKeys.LegacyFingerprint("a b c d"));
        Assert.True(Codes.IsValidGtin("7891234567895"));
        Assert.Equal("weight_kg: 2.5 vs 15", ProductAttributes.Conflict("Ração 2,5kg", "Ração 15kg"));
    }

    [Fact]
    public void DuplicateIdsAreRefused() =>
        Assert.Throws<ArgumentException>(() => Matcher.Match(new[] { new Record("1", "a"), new Record("1", "b") }));

    [Fact]
    public void PairwiseScores()
    {
        var s = Evaluation.Pairwise(new Dictionary<string, int> { ["1"] = 1, ["2"] = 1, ["3"] = 2 },
            new Dictionary<string, string> { ["1"] = "x", ["2"] = "x", ["3"] = "x" });
        Assert.Equal(1.0, s.Precision);
        Assert.Equal(3, s.TruePairs);
    }
}
