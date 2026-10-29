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
    public void AttributeRulesFoundOnRealPairs()
    {
        Assert.Null(ProductAttributes.Conflict("Forno 110V", "Forno 127V"));
        Assert.Null(ProductAttributes.Conflict("Concha Inox", "Concha Prata"));
        Assert.Equal("size: 38 vs 40", ProductAttributes.Conflict("Bota - 38 - Preto", "Bota - 40 - Preto"));
        Assert.Equal("quantity: 3 vs 6", ProductAttributes.Conflict("Meia Kit 3 Pares", "Meia Kit 6 Pares"));
        Assert.Equal("dimensions: 20x30 vs 30x40", ProductAttributes.Conflict("Quadro 20x30", "Quadro 30x40"));
        Assert.Null(ProductAttributes.Conflict("Porta Escova 10,6 X 8,5 X 10,6 Cm", "Porta Escova 10,6x8,5cm"));
        Assert.Null(ProductAttributes.Conflict("Toalha 1,50 x 2,00 m", "Toalha 150x200cm"));
        Assert.Equal("screen_in: 55 vs 40", ProductAttributes.Conflict("TV 55\" Samsung", "TV 40\" Samsung"));
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

    // Counterexamples from the 2019 key experiments (evaluation/keys_benchmark.md), as in python/tests/test_text.py.
    private static readonly Func<string, string>[] ShippedKeys =
        { TextKeys.Fingerprint, TextKeys.TokenKey, TextKeys.PhoneticKey, t => TextKeys.NgramFingerprint(t) };

    [Theory]
    [InlineData("DVD Canta Rio 98", "Dvd - Centurião")]
    [InlineData("Acabamento para Registro Gaveta 1 1/2\" LK Cromado - 4900.C17.GD - Deca - Deca", "Bandagem Vollke Elastica Preta 5 Metros")]
    public void CounterexamplesOfDroppedKeysStayApart(string a, string b)
    {
        foreach (var key in ShippedKeys)
            Assert.NotEqual(key(a), key(b));
    }

    [Fact]
    public void NumbersArePartOfTheKey() =>
        Assert.NotEqual(TextKeys.PhoneticKey("Shampoo Aussie Moist 865ML"), TextKeys.PhoneticKey("Shampoo Aussie Moist 180 Ml"));

    [Fact]
    public void KnownLimits()
    {
        Assert.NotEqual(TextKeys.PhoneticKey("Hambúrguer"), TextKeys.PhoneticKey("Hamburger"));
        Assert.NotEqual(TextKeys.Normalize("lav¨¢vel"), TextKeys.Normalize("lavável"));
    }
}
