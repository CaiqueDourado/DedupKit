namespace DedupKit;

/// <summary>One listing. Only <see cref="Id"/> and <see cref="Name"/> are required.</summary>
public sealed record Record(
    string Id,
    string Name,
    string Brand = "",
    IReadOnlyList<string>? Codes = null,
    string Url = "",
    string Image = "",
    string Source = "")
{
    /// <summary>Barcodes or SKUs (never null).</summary>
    public IReadOnlyList<string> CodeList => Codes ?? Array.Empty<string>();
}

/// <summary>
/// A blocking key: records with the same non-empty value are candidates. With
/// <see cref="NeedsSharedWord"/>, a pair is accepted only if the two names share a word.
/// </summary>
public sealed record Rule(string Name, Func<Record, IReadOnlyList<string>> Keys, bool NeedsSharedWord = false);

/// <summary>Two records linked by a rule.</summary>
public sealed record Link(string A, string B, string Rule, string Value);

/// <summary>A candidate pair that was refused, and why.</summary>
public sealed record Rejected(string A, string B, string Rule, string Value, string Reason);

/// <summary>A key value shared by too many records to mean anything (a placeholder image, for example).</summary>
public sealed record SkippedBlock(string Rule, string Value, int Size);

/// <summary>Clustering mode.</summary>
public enum MatchMode
{
    /// <summary>Linked records, directly or through others, form one cluster. Independent of input order.</summary>
    Connected,

    /// <summary>The 2019 algorithm: neighbours and their neighbours join the oldest cluster among them.</summary>
    TwoHop,
}

/// <summary>Options of <see cref="Matcher.Match"/>.</summary>
public sealed class MatchOptions
{
    /// <summary>Rules, in order (default: <see cref="Rules.Default"/>).</summary>
    public IReadOnlyList<Rule>? Rules { get; init; }

    /// <summary>Clustering mode.</summary>
    public MatchMode Mode { get; init; } = MatchMode.Connected;

    /// <summary>Key values shared by more records than this are skipped.</summary>
    public int MaxBlock { get; init; } = 100;

    /// <summary>Codes to ignore; null means <see cref="Matcher.CodeBlacklist"/>.</summary>
    public IReadOnlySet<string>? Blacklist { get; init; }

    /// <summary>Refuse pairs whose names state different sizes, voltages, memories, colours or genders.</summary>
    public bool CheckAttributes { get; init; } = true;

    /// <summary>Also refuse pairs whose brand fields differ (off: marketplaces put the seller in the brand field).</summary>
    public bool CheckBrands { get; init; }
}

/// <summary>Result of <see cref="Matcher.Match"/>.</summary>
public sealed class MatchResult
{
    internal MatchResult(
        IReadOnlyDictionary<string, int> clusterOf,
        IReadOnlyDictionary<string, (string Rule, string Value)> via,
        IReadOnlyList<Link> links,
        IReadOnlyList<Rejected> rejected,
        IReadOnlyList<SkippedBlock> skipped,
        IReadOnlyList<string> order)
    {
        ClusterOf = clusterOf;
        Via = via;
        Links = links;
        Rejected = rejected;
        Skipped = skipped;
        _order = order;
    }

    private readonly IReadOnlyList<string> _order;

    /// <summary>Cluster number (1, 2, ... in input order) of every id.</summary>
    public IReadOnlyDictionary<string, int> ClusterOf { get; }

    /// <summary>The rule and key value that brought each record into its cluster.</summary>
    public IReadOnlyDictionary<string, (string Rule, string Value)> Via { get; }

    /// <summary>Links that formed the clusters (audit trail).</summary>
    public IReadOnlyList<Link> Links { get; }

    /// <summary>Refused pairs.</summary>
    public IReadOnlyList<Rejected> Rejected { get; }

    /// <summary>Skipped key values.</summary>
    public IReadOnlyList<SkippedBlock> Skipped { get; }

    /// <summary>Clusters with two or more records, in order of their first record.</summary>
    public IReadOnlyList<IReadOnlyList<string>> Clusters =>
        _order.GroupBy(id => ClusterOf[id]).OrderBy(g => g.Key).Where(g => g.Count() > 1)
            .Select(g => (IReadOnlyList<string>)g.ToList()).ToList();
}

/// <summary>The default rules: the 2019 catalog's keys, in its order, with the fingerprint bug fixed.</summary>
public static class Rules
{
    /// <summary>Brand values that say nothing.</summary>
    public static readonly IReadOnlySet<string> GenericBrands = new HashSet<string>(new[]
    {
        "brand", "marca", "importado", "produto importado", "original", "nao informado", "indisponivel",
        "n a", "n d", "na", "nd", "generico", "generica", "sem marca", "outros", "outras", "diversos", "varios",
    }, StringComparer.Ordinal);

    internal static string? BrandOk(string? brand)
    {
        var b = TextKeys.Normalize(brand);
        return b.Length < 3 || GenericBrands.Contains(b) ? null : b;
    }

    private static IReadOnlyList<string> Sorted(IEnumerable<string> values) =>
        values.Distinct(StringComparer.Ordinal).OrderBy(v => v, StringComparer.Ordinal).ToList();

    private static IReadOnlyList<string> One(bool ok, string value) => ok ? new[] { value } : Array.Empty<string>();

    private static IReadOnlyList<string> LongCodes(Record r) =>
        Sorted(r.CodeList.Where(c => Codes.Classify(c) == "long").Select(Codes.Clean));

    private static Func<Record, IReadOnlyList<string>> ShortCodesWith(Func<string, string> brandKey) => r =>
    {
        var b = BrandOk(r.Brand);
        if (b is null)
        {
            return Array.Empty<string>();
        }

        var k = brandKey(b);
        return Sorted(r.CodeList.Where(c => Codes.Classify(c) == "short").Select(c => Codes.Clean(c) + "|" + k));
    };

    private static IReadOnlyList<string> NameExact(Record r)
    {
        var n = TextKeys.Normalize(r.Name);
        return One(TextKeys.Tokens(n).Length >= 2, n);
    }

    private static IReadOnlyList<string> NameFingerprint(Record r) =>
        One(TextKeys.Tokens(r.Name).Distinct(StringComparer.Ordinal).Count() >= 3, TextKeys.Fingerprint(r.Name));

    private static IReadOnlyList<string> LegacyNameFingerprint(Record r) =>
        One(TextKeys.Tokens(r.Name).Distinct(StringComparer.Ordinal).Count() >= 3, TextKeys.LegacyFingerprint(r.Name));

    private static IReadOnlyList<string> NamePhonetic(Record r)
    {
        var k = TextKeys.PhoneticKey(r.Name);
        return One(k.Length > 3 && k.Contains(' ', StringComparison.Ordinal), k);
    }

    private static IReadOnlyList<string> NameNgram(Record r) =>
        One(TextKeys.Normalize(r.Name).Replace(" ", string.Empty, StringComparison.Ordinal).Length >= 10, TextKeys.NgramFingerprint(r.Name));

    private static IReadOnlyList<string> NameTokens(Record r)
    {
        var k = TextKeys.TokenKey(r.Name);
        return One(k.Contains(' ', StringComparison.Ordinal), k);
    }

    private static IReadOnlyList<string> Url(Record r)
    {
        var u = TextKeys.NormalizeUrl(r.Url);
        return One(u.Length > 0, u);
    }

    private static IReadOnlyList<string> Image(Record r)
    {
        var image = (r.Image ?? string.Empty).Trim(' ', '\t', '\r', '\n');
        return One(image.Length > 0, image);
    }

    /// <summary>All rules, in the 2019 order, with the fingerprint fixed.</summary>
    public static readonly IReadOnlyList<Rule> Default = new[]
    {
        new Rule("code", LongCodes, NeedsSharedWord: true),
        new Rule("name", NameExact),
        new Rule("name_fingerprint", NameFingerprint),
        new Rule("name_phonetic", NamePhonetic),
        new Rule("name_ngram", NameNgram),
        new Rule("name_tokens", NameTokens),
        new Rule("url", Url),
        new Rule("short_code_brand", ShortCodesWith(TextKeys.Fingerprint)),
        new Rule("short_code_brand_ngram", ShortCodesWith(b => TextKeys.NgramFingerprint(b))),
        new Rule("image", Image),
    };

    /// <summary>Same as <see cref="Default"/> with the 2019 fingerprint (keeps every other word).</summary>
    public static readonly IReadOnlyList<Rule> Legacy =
        Default.Select(r => r.Name == "name_fingerprint" ? new Rule("name_fingerprint", LegacyNameFingerprint) : r).ToList();

    /// <summary>Picks default rules by name, in the given order.</summary>
    public static IReadOnlyList<Rule> ByName(params string[] names) =>
        names.Select(n => Default.First(r => r.Name == n)).ToList();
}

/// <summary>Groups records that are the same product, and records why.</summary>
public static class Matcher
{
    private static readonly HashSet<string> CodeRules = new(StringComparer.Ordinal) { "code", "short_code_brand", "short_code_brand_ngram" };

    /// <summary>
    /// Codes that cannot identify a product: used by more than <paramref name="maxPerSource"/> listings
    /// of the same store, or letters-only codes used by more than one listing.
    /// </summary>
    public static IReadOnlySet<string> CodeBlacklist(IEnumerable<Record> records, int maxPerSource = 5)
    {
        var perSource = new Dictionary<(string, string), int>();
        var lettersOnly = new Dictionary<string, int>(StringComparer.Ordinal);
        foreach (var r in records)
        {
            foreach (var c in r.CodeList.Select(Codes.Clean).Distinct(StringComparer.Ordinal))
            {
                if (c.Length == 0)
                {
                    continue;
                }

                var key = (r.Source ?? string.Empty, c);
                perSource[key] = perSource.GetValueOrDefault(key) + 1;
                if (c.All(ch => ch is >= 'A' and <= 'Z'))
                {
                    lettersOnly[c] = lettersOnly.GetValueOrDefault(c) + 1;
                }
            }
        }

        var bad = new HashSet<string>(StringComparer.Ordinal);
        foreach (var ((_, c), n) in perSource)
        {
            if (n > maxPerSource)
            {
                bad.Add(c);
            }
        }

        foreach (var (c, n) in lettersOnly)
        {
            if (n > 1)
            {
                bad.Add(c);
            }
        }

        return bad;
    }

    /// <summary>Groups the records. See <see cref="MatchOptions"/>.</summary>
    public static MatchResult Match(IEnumerable<Record> records, MatchOptions? options = null)
    {
        options ??= new MatchOptions();
        var recs = records.ToList();
        var ids = recs.Select(r => r.Id).ToList();
        if (ids.Distinct(StringComparer.Ordinal).Count() != ids.Count)
        {
            throw new ArgumentException("Record ids must be unique.", nameof(records));
        }

        var rules = options.Rules ?? Rules.Default;
        var badCodes = options.Blacklist ?? CodeBlacklist(recs);
        var attrs = options.CheckAttributes ? recs.Select(r => ProductAttributes.Extract(r.Name)).ToList() : null;
        var brands = options.CheckBrands ? recs.Select(r => Rules.BrandOk(r.Brand)).ToList() : null;
        var nameWords = options.CheckBrands ? recs.Select(r => TextKeys.Tokens(r.Name).ToHashSet(StringComparer.Ordinal)).ToList() : null;

        var rejected = new List<Rejected>();
        var skipped = new List<SkippedBlock>();
        var neighbours = recs.Select(_ => new Dictionary<int, (string Rule, string Value)>()).ToList();
        var edges = new List<(int I, int J, string Rule, string Value)>();

        foreach (var rule in rules)
        {
            var blocks = new Dictionary<string, List<int>>(StringComparer.Ordinal);
            for (var i = 0; i < recs.Count; i++)
            {
                foreach (var v in rule.Keys(recs[i]))
                {
                    if (string.IsNullOrEmpty(v))
                    {
                        continue;
                    }

                    if (CodeRules.Contains(rule.Name) && badCodes.Contains(v.Split('|', 2)[0]))
                    {
                        continue;
                    }

                    if (!blocks.TryGetValue(v, out var list))
                    {
                        list = new List<int>();
                        blocks[v] = list;
                    }

                    list.Add(i);
                }
            }

            foreach (var value in blocks.Keys.OrderBy(k => k, StringComparer.Ordinal))
            {
                var members = blocks[value];
                if (members.Count < 2)
                {
                    continue;
                }

                if (members.Count > options.MaxBlock)
                {
                    skipped.Add(new SkippedBlock(rule.Name, value, members.Count));
                    continue;
                }

                for (var x = 0; x < members.Count; x++)
                {
                    for (var y = x + 1; y < members.Count; y++)
                    {
                        int i = members[x], j = members[y];
                        if (neighbours[i].ContainsKey(j))
                        {
                            continue;
                        }

                        if (rule.NeedsSharedWord && !TextKeys.SharesWord(recs[i].Name, recs[j].Name))
                        {
                            rejected.Add(new Rejected(ids[i], ids[j], rule.Name, value, "names share no word"));
                            continue;
                        }

                        var why = (attrs is null ? null : ProductAttributes.Conflict(attrs[i], attrs[j]))
                                  ?? (brands is null ? null : BrandConflict(i, j, brands, nameWords!));
                        if (why is not null)
                        {
                            rejected.Add(new Rejected(ids[i], ids[j], rule.Name, value, why));
                            continue;
                        }

                        neighbours[i][j] = (rule.Name, value);
                        neighbours[j][i] = (rule.Name, value);
                        edges.Add((i, j, rule.Name, value));
                    }
                }
            }
        }

        return options.Mode == MatchMode.Connected
            ? Connected(recs.Count, ids, edges, rejected, skipped)
            : TwoHop(recs.Count, ids, neighbours, rejected, skipped);
    }

    private static string? BrandConflict(int i, int j, List<string?> brands, List<HashSet<string>> nameWords)
    {
        string? a = brands[i], b = brands[j];
        if (a is null || b is null || a == b)
        {
            return null;
        }

        if (a.Split(' ').All(nameWords[j].Contains) || b.Split(' ').All(nameWords[i].Contains))
        {
            return null;
        }

        return $"brand: {a} vs {b}";
    }

    private static MatchResult Connected(int n, List<string> ids, List<(int I, int J, string Rule, string Value)> edges,
        List<Rejected> rejected, List<SkippedBlock> skipped)
    {
        var parent = Enumerable.Range(0, n).ToArray();

        int Find(int i)
        {
            while (parent[i] != i)
            {
                parent[i] = parent[parent[i]];
                i = parent[i];
            }

            return i;
        }

        var links = new List<Link>();
        var via = new Dictionary<string, (string Rule, string Value)>(StringComparer.Ordinal);
        foreach (var (i, j, rule, value) in edges)
        {
            int ri = Find(i), rj = Find(j);
            if (ri != rj)
            {
                parent[Math.Max(ri, rj)] = Math.Min(ri, rj);
                links.Add(new Link(ids[i], ids[j], rule, value));
                via.TryAdd(ids[j], (rule, value));
                via.TryAdd(ids[i], (rule, value));
            }
        }

        var number = new Dictionary<int, int>();
        var clusterOf = new Dictionary<string, int>(StringComparer.Ordinal);
        for (var i = 0; i < n; i++)
        {
            var root = Find(i);
            if (!number.TryGetValue(root, out var c))
            {
                c = number.Count + 1;
                number[root] = c;
            }

            clusterOf[ids[i]] = c;
        }

        return new MatchResult(clusterOf, via, links, rejected, skipped, ids);
    }

    private static MatchResult TwoHop(int n, List<string> ids, List<Dictionary<int, (string Rule, string Value)>> neighbours,
        List<Rejected> rejected, List<SkippedBlock> skipped)
    {
        var group = new int?[n];
        var via = new Dictionary<string, (string Rule, string Value)>(StringComparer.Ordinal);
        var links = new List<Link>();
        var nextGroup = 1;
        for (var seed = 0; seed < n; seed++)
        {
            if (group[seed] is not null)
            {
                continue;
            }

            var hop1 = neighbours[seed].Keys.OrderBy(k => k).ToList();
            var reached = new Dictionary<int, (int From, string Rule, string Value)>();
            foreach (var h in hop1)
            {
                var (rule, value) = neighbours[seed][h];
                reached[h] = (seed, rule, value);
            }

            foreach (var h in hop1)
            {
                foreach (var m in neighbours[h].Keys.OrderBy(k => k))
                {
                    if (m != seed && !reached.ContainsKey(m))
                    {
                        var (rule, value) = neighbours[h][m];
                        reached[m] = (h, rule, value);
                    }
                }
            }

            var members = new List<int> { seed };
            members.AddRange(reached.Keys.OrderBy(k => k));
            var existing = members.Where(m => group[m] is not null).Select(m => group[m]!.Value).ToList();
            int target;
            if (existing.Count > 0)
            {
                target = existing.Min();
            }
            else
            {
                target = nextGroup++;
            }

            foreach (var m in members)
            {
                if (group[m] is null)
                {
                    group[m] = target;
                    if (reached.TryGetValue(m, out var r))
                    {
                        via[ids[m]] = (r.Rule, r.Value);
                        links.Add(new Link(ids[r.From], ids[m], r.Rule, r.Value));
                    }
                }
            }
        }

        var number = new Dictionary<int, int>();
        var clusterOf = new Dictionary<string, int>(StringComparer.Ordinal);
        for (var i = 0; i < n; i++)
        {
            var g = group[i]!.Value;
            if (!number.TryGetValue(g, out var c))
            {
                c = number.Count + 1;
                number[g] = c;
            }

            clusterOf[ids[i]] = c;
        }

        return new MatchResult(clusterOf, via, links, rejected, skipped, ids);
    }
}
