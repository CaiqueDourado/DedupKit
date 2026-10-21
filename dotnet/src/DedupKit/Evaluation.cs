namespace DedupKit;

/// <summary>Pairwise scores: a pair of records is a positive when both are in the same cluster.</summary>
public sealed record Scores(double Precision, double Recall, double F1, long TruePairs, long PredictedPairs, long CorrectPairs);

/// <summary>Measures a clustering against known answers.</summary>
public static class Evaluation
{
    private static long Pairs(long n) => n * (n - 1) / 2;

    /// <summary>Pairwise precision, recall and F1 of predicted (id → cluster) against truth (id → entity).</summary>
    public static Scores Pairwise<TCluster, TEntity>(IReadOnlyDictionary<string, TCluster> predicted, IReadOnlyDictionary<string, TEntity> truth)
        where TCluster : notnull
        where TEntity : notnull
    {
        var ids = predicted.Keys.Where(truth.ContainsKey).ToList();
        long predictedPairs = ids.GroupBy(i => predicted[i]).Sum(g => Pairs(g.Count()));
        long truePairs = ids.GroupBy(i => truth[i]).Sum(g => Pairs(g.Count()));
        long correct = ids.GroupBy(i => (predicted[i], truth[i])).Sum(g => Pairs(g.Count()));
        var p = predictedPairs > 0 ? (double)correct / predictedPairs : 1.0;
        var r = truePairs > 0 ? (double)correct / truePairs : 1.0;
        var f = p + r > 0 ? 2 * p * r / (p + r) : 0.0;
        return new Scores(p, r, f, truePairs, predictedPairs, correct);
    }

    /// <summary>For each rule: links made and the share that joined two records of the same entity.</summary>
    public static IReadOnlyDictionary<string, (int Links, double Precision)> LinkPrecision<TEntity>(MatchResult result, IReadOnlyDictionary<string, TEntity> truth)
        where TEntity : notnull
    {
        return result.Links.Where(l => truth.ContainsKey(l.A) && truth.ContainsKey(l.B))
            .GroupBy(l => l.Rule)
            .ToDictionary(g => g.Key, g => (g.Count(), g.Count(l => truth[l.A].Equals(truth[l.B])) / (double)g.Count()));
    }
}
